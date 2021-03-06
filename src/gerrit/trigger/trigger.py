import json
import os
import logging
import traceback
import datetime
import time

import requests
import psycopg2
import paramiko

FORMAT = '%(asctime)-15s %(levelno)s %(message)s'
logging.basicConfig(format=FORMAT, level=logging.INFO)
logger = logging.getLogger("gerrit")

def get_env(name):
    if name not in os.environ:
        raise Exception("%s not set" % name)
    return os.environ[name]


def main():
    get_env('INFRABOX_SERVICE')
    get_env('INFRABOX_VERSION')
    pg_db = get_env('INFRABOX_DATABASE_DB')
    pg_user = get_env('INFRABOX_DATABASE_USER')
    pg_password = get_env('INFRABOX_DATABASE_PASSWORD')
    pg_host = get_env('INFRABOX_DATABASE_HOST')
    pg_port = int(get_env('INFRABOX_DATABASE_PORT'))
    gerrit_port = int(get_env('INFRABOX_GERRIT_PORT'))
    gerrit_hostname = get_env('INFRABOX_GERRIT_HOSTNAME')
    gerrit_username = get_env('INFRABOX_GERRIT_USERNAME')
    gerrit_key_filename = get_env('INFRABOX_GERRIT_KEY_FILENAME')

    while True:
        r = requests.get("http://localhost:4040", timeout=5)
        leader = r.json()['name']

        if leader == os.environ['HOSTNAME']:
            logger.info("I'm the leader")
            break
        else:
            logger.info("I'm not the leader, %s is the leader", leader)
            time.sleep(1)

    conn = psycopg2.connect(dbname=pg_db,
                            user=pg_user,
                            password=pg_password,
                            host=pg_host,
                            port=pg_port)

    logger.info("Connected to db")
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(username=gerrit_username,
                   hostname=gerrit_hostname,
                   port=gerrit_port,
                   key_filename=gerrit_key_filename)
    client.get_transport().set_keepalive(60)

    logger.info("Connected to gerrit")
    _, stdout, _ = client.exec_command('gerrit stream-events')

    logger.info("Waiting for stream-events")
    for line in stdout:
        event = json.loads(line)

        if event['type'] == "patchset-created":
            logger.info(json.dumps(event, indent=4))
            handle_patchset_created(conn, event)

def handle_patchset_created_project(conn, event, project_id, project_name):
    if event['patchSet']['isDraft']:
        return

    c = conn.cursor()
    c.execute('SELECT id FROM repository WHERE project_id = %s', [project_id])
    result = c.fetchone()
    c.close()

    repository_id = result[0]
    sha = event['patchSet']['revision']

    logger.info("Repository ID: %s", repository_id)

    c = conn.cursor()
    c.execute('SELECT * FROM "commit" WHERE project_id = %s and id = %s', [project_id, sha])
    result = c.fetchone()
    c.close()

    print result

    commit = result

    if not commit:
        c = conn.cursor()
        c.execute('''
            INSERT INTO "commit" (
                id, message, repository_id, timestamp,
                author_name, author_email, author_username,
                committer_name, committer_email, committer_username, url, branch, project_id, tag)
            VALUES (%s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s, %s)
            RETURNING *
                ''', (sha, event['change']['commitMessage'], repository_id, datetime.datetime.now(), event['change']['owner']['name'],
                      '', event['change']['owner']['username'], '', '', '',
                      event['change']['url'],
                      event['change']['branch'], project_id, None))
        result = c.fetchone()
        c.close()
        commit = result

    print commit

    c = conn.cursor()
    c.execute('''SELECT count(distinct build_number) + 1 AS build_no
              FROM build AS b
              WHERE b.project_id = %s''', [project_id])
    result = c.fetchone()
    c.close()

    build_no = result[0]
    c = conn.cursor()
    c.execute('''INSERT INTO build (commit_id, build_number, project_id)
                 VALUES (%s, %s, %s)
                 RETURNING id''', (sha, build_no, project_id))
    result = c.fetchone()
    c.close()

    build_id = result[0]

    env_vars = {
        "INFRABOX_GERRIT_PATCHSET_UPLOADER_USERNAME": event['patchSet']['uploader']['username'],
        "INFRABOX_GERRIT_PATCHSET_UPLOADER_NAME": event['patchSet']['uploader']['name'],
        "INFRABOX_GERRIT_PATCHSET_UPLOADER_EMAIL": event['patchSet']['uploader']['email'],
        "INFRABOX_GERRIT_PATCHSET_REF": event['patchSet']['ref'],
        "INFRABOX_GERRIT_PATCHSET_REVISION": event['patchSet']['revision'],
        "INFRABOX_GERRIT_CHANGE_STATUS": event['change']['status'],
        "INFRABOX_GERRIT_CHANGE_URL": event['change']['url'],
        "INFRABOX_GERRIT_CHANGE_COMMIT_MESSAGE": event['change']['commitMessage'],
        "INFRABOX_GERRIT_CHANGE_NUMBER": event['change']['number'],
        "INFRABOX_GERRIT_CHANGE_PROJECT": event['change']['project'],
        "INFRABOX_GERRIT_CHANGE_BRANCH": event['change']['branch'],
        "INFRABOX_GERRIT_CHANGE_ID": event['change']['id'],
        "INFRABOX_GERRIT_CHANGE_SUBJECT": event['change']['subject'],
        "INFRABOX_GERRIT_CHANGE_OWNER_USERNAME": event['change']['owner']['username'],
        "INFRABOX_GERRIT_CHANGE_OWNER_NAME": event['change']['owner']['name'],
        "INFRABOX_GERRIT_CHANGE_OWNER_EMAIL": event['change']['owner']['email'],
        "INFRABOX_GERRIT_UPLOADER_USERNAME": event['uploader']['username'],
        "INFRABOX_GERRIT_UPLOADER_NAME": event['uploader']['name'],
        "INFRABOX_GERRIT_UPLOADER_EMAIL": event['uploader']['email']
    }

    git_repo = {
        "commit": sha,
        "clone_url": "ssh://%s@%s:%s/%s" % (get_env('INFRABOX_GERRIT_USERNAME'),
                                            get_env('INFRABOX_GERRIT_HOSTNAME'),
                                            get_env('INFRABOX_GERRIT_PORT'),
                                            project_name),
        "ref": event['patchSet']['ref']
    }

    c = conn.cursor()
    c.execute('''INSERT INTO job (id, state, build_id, type, name,
                                 project_id, build_only, dockerfile,
                                 cpu, memory, repo, env_var)
                VALUES (gen_random_uuid(), 'queued', %s, 'create_job_matrix', 'Create Jobs',
                        %s, false, '', 1, 1024, %s, %s)''', (build_id, project_id, json.dumps(git_repo), json.dumps(env_vars)))

def handle_patchset_created(conn, event):
    conn.rollback()

    project_name = event.get('project', None)

    if not project_name:
        project_name = event['change'].get('project', None)

    if not project_name:
        logger.error('Failed to get project from event')
        return


    logger.info("Project name: %s", project_name)

    # Get project
    c = conn.cursor()
    c.execute("SELECT id FROM project WHERE name = %s AND type='gerrit'", [project_name])
    projects = c.fetchall()
    c.close()

    logger.info("Found projects in db: %s", json.dumps(projects))

    if not projects:
        return

    for project in projects:
        project_id = project[0]
        logger.info("Handling project with id: %s", project_id)
        handle_patchset_created_project(conn, event, project_id, project_name)

    conn.commit()

def print_stackdriver():
    if 'INFRABOX_GENERAL_LOG_STACKDRIVER' in os.environ and os.environ['INFRABOX_GENERAL_LOG_STACKDRIVER'] == 'true':
        print json.dumps({
            "serviceContext": {
                "service": os.environ.get('INFRABOX_SERVICE', 'unknown'),
                "version": os.environ.get('INFRABOX_VERSION', 'unknown')
            },
            "message": traceback.format_exc(),
            "severity": 'ERROR'
        })
    else:
        print traceback.format_exc()

if __name__ == "__main__":
    try:
        main()
    except:
        print_stackdriver()
