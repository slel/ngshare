import sys
import json
import simplejson
import base64
import requests

URL_PREFIX = 'http://127.0.0.1:11111'
GET = requests.get
POST = requests.post
user = None

def request_page(url, data={}, params={}, method=GET) :
	assert url.startswith('/') and not url.startswith('//')
	resp = method(URL_PREFIX + url, data=data, params=params)
	return resp.json()

def assert_success(url, data={}, params={}, method=GET) :
	global user
	if user is not None :
		params = params.copy()
		params['user'] = user
	resp = request_page(url, data, params, method)
	if resp['success'] != True :
		print(repr(resp), file=sys.stderr)
		raise Exception('Not success')
	return resp

def assert_fail(url, data={}, params={}, method=GET, msg=None) :
	global user
	if user is not None :
		params = params.copy()
		params['user'] = user
	resp = request_page(url, data, params, method)
	if resp['success'] != False :
		print(repr(resp), file=sys.stderr)
		raise Exception('Success')
	if msg is not None :
		assert resp['message'] == msg
	return resp

# Run init.py before running the test

def test_init() :
	import os, time
	from settings import DB_NAME
	assert DB_NAME.startswith('sqlite:///')
	os.unlink(DB_NAME[len('sqlite:///'):])
	os.system('touch vserver.py')
	time.sleep(2)

def test_list_courses() :
	url = '/api/courses'
	global user
	user = None
	assert_fail(url, msg='Login required (Please supply user)')
	user = 'Nobody'
	assert_fail(url, msg='Login required (User not found)')
	user = 'Kevin'
	assert assert_success(url)['courses'] == ['course1']
	user = 'Abigail'
	assert assert_success(url)['courses'] == ['course2']
	user = 'Lawrence'
	assert assert_success(url)['courses'] == ['course1']
	user = 'Eric'
	assert assert_success(url)['courses'] == ['course2']

def test_add_courses() :
	url = '/api/course/'
	global user
	user = None
	assert_fail(url + 'course3', method=POST,
				msg='Login required (Please supply user)')
	user = 'Erics'
	assert_fail(url + 'course3', method=POST,
				msg='Login required (User not found)')
	user = 'Eric'
	assert_success(url + 'course3', method=POST)
	assert_fail(url + 'course3', method=POST, msg='Course already exists')
	assert assert_success('/api/courses')['courses'] == ['course2', 'course3']

def test_list_assignments() :
	url = '/api/assignments/'
	global user
	user = 'Kevin'
	assert_fail(url + 'course2',
				msg='Permission denied (not related to course)')
	user = 'Abigail'
	assert assert_success(url + 'course2')['assignments'] == \
			['assignment2a', 'assignment2b']
	user = 'Lawrence'
	assert_fail(url + 'course2',
				msg='Permission denied (not related to course)')
	user = 'Eric'
	assert assert_success(url + 'course2')['assignments'] == \
			['assignment2a', 'assignment2b']
	assert_fail(url + 'jkl', msg='Course not found')

def test_download_assignment() :
	url = '/api/assignment/'
	global user
	user = 'Kevin'
	files = assert_success(url + 'course1/challenge')['files']
	assert files[0]['path'] == 'file2'
	assert base64.b64decode(files[0]['content'].encode()) == b'22222'
	assert_fail(url + 'jkl/challenger', msg='Course not found')
	assert_fail(url + 'course1/challenger', msg='Assignment not found')
	# Check list_only
	files = assert_success(url + 'course1/challenge?list_only=true')['files']
	assert list(files[0]) == ['path']
	assert files[0]['path'] == 'file2'
	user = 'Eric'
	assert_fail(url + 'course1/challenge',
				msg='Permission denied (not related to course)')

def test_release_assignment() :
	url = '/api/assignment/'
	global user
	data = {'files': json.dumps([{'path': 'a', 'content': 'amtsCg=='},
									{'path': 'b', 'content': 'amtsCg=='}])}
	user = 'Kevin'
	assert_fail(url + 'jkl/challenger', method=POST, 
				data=data, msg='Course not found')
	assert_fail(url + 'course1/challenger', method=POST,
				msg='Please supply files')
	assert_success(url + 'course1/challenger', method=POST, 
					data=data)
	assert_fail(url + 'course1/challenger', method=POST, 
				data=data, msg='Assignment already exists')
	data['files'] = json.dumps([{'path': 'a', 'content': 'amtsCg'}])
	assert_fail(url + 'course1/challenges', method=POST, 
				data=data, msg='Content cannot be base64 decoded')
	for pathname in ['/a', '/', '', '../etc', 'a/./a.py', 'a/.'] :
		data['files'] = json.dumps([{'path': pathname, 'content': ''}])
		assert_fail(url + 'course1/challenges', method=POST, 
					data=data, msg='Illegal path')
	user = 'Abigail'
	assert_fail(url + 'course1/challenger', method=POST, 
				data=data, msg='Permission denied (not course instructor)')
	user = 'Lawrence'
	assert_fail(url + 'course1/challenger', method=POST, 
				data=data, msg='Permission denied (not course instructor)')
	user = 'Eric'
	assert_fail(url + 'course1/challenger', method=POST, 
				data=data, msg='Permission denied (not course instructor)')

def test_list_submissions() :
	url = '/api/submissions/'
	global user
	user = 'Kevin'
	assert_fail(url + 'jkl/challenge', msg='Course not found')
	assert_fail(url + 'course1/challenges',
				msg='Assignment not found')
	result = assert_success(url + 'course1/challenge')
	assert len(result['submissions']) == 2
	assert set(result['submissions'][0]) == {'student_id', 'timestamp'}
	assert result['submissions'][0]['student_id'] == 'Lawrence'
	assert result['submissions'][1]['student_id'] == 'Lawrence'
	user = 'Abigail'
	result = assert_success(url + 'course2/assignment2a')
	assert len(result['submissions']) == 0
	user = 'Eric'
	assert_fail(url + 'course1/challenges',
				msg='Permission denied (not course instructor)')
	assert_fail(url + 'course2/assignment2a',
				msg='Permission denied (not course instructor)')

def test_list_student_submission() :
	url = '/api/submissions/'
	global user
	user = 'Kevin'
	assert_fail(url + 'jkl/challenge/st', msg='Course not found')
	assert_fail(url + 'course1/challenges/st', msg='Assignment not found')
	assert_fail(url + 'course1/challenge/st', msg='Student not found')
	result = assert_success(url + 'course1/challenge/Lawrence')
	assert len(result['submissions']) == 2
	assert set(result['submissions'][0]) == {'student_id', 'timestamp'}
	user = 'Eric'
	result = assert_success(url + 'course2/assignment2a/Eric')
	assert len(result['submissions']) == 0
	user = 'Kevin'
	assert_fail(url + 'course2/assignment2a/Eric',
				msg='Permission denied (not course instructor)')
	user = 'Abigail'
	assert_fail(url + 'course1/challenge/Lawrence',
				msg='Permission denied (not course instructor)')
	user = 'Lawrence'
	assert_success(url + 'course1/challenge/Lawrence')
	user = 'Eric'
	assert_fail(url + 'course1/challenge/Lawrence',
				msg='Permission denied (not course instructor)')

def test_submit_assignment() :
	url = '/api/submission/'
	global user
	user = 'Kevin'
	data = {'files': json.dumps([{'path': 'a', 'content': 'amtsCg=='},
									{'path': 'b', 'content': 'amtsCg=='}])}
	assert_fail(url + 'jkl/challenge', method=POST,
				msg='Course not found')
	assert_fail(url + 'course1/challenges', method=POST,
				msg='Assignment not found')
	user = 'Lawrence'
	assert_fail(url + 'course1/challenge', method=POST,
				msg='Please supply files')
	assert_success(url + 'course1/challenge', method=POST, data=data)
	data['files'] = json.dumps([{'path': 'a', 'content': 'amtsCg=='}])
	assert_success(url + 'course1/challenge',
			method=POST, data=data)
	data['files'] = json.dumps([{'path': 'a', 'content': 'amtsCg'}])
	assert_fail(url + 'course1/challenge', method=POST,
				data=data, msg='Content cannot be base64 decoded')
	user = 'Kevin'
	result = assert_success('/api/submissions/course1/challenge')
	assert len(result['submissions']) == 4	# 2 from init, 2 from this
	user = 'Eric'
	assert_fail(url + 'course1/challenge', method=POST,
				msg='Permission denied (not related to course)')

def test_download_submission() :
	url = '/api/submission/'
	global user
	user = 'Kevin'
	assert_fail(url + 'jkl/challenge/st', msg='Course not found')
	assert_fail(url + 'course1/challenges/st', msg='Assignment not found')
	assert_fail(url + 'course1/challenge/st', msg='Student not found')
	result = assert_success(url + 'course1/challenge/Lawrence')
	assert len(result['files']) == 1
	assert next(filter(lambda x: x['path'] == 'a', result['files'])) \
			['content'].replace('\n', '') == 'amtsCg=='
	user = 'Abigail'
	assert_fail(url + 'course2/assignment2a/Eric', msg='Submission not found')
	# Check list_only
	user = 'Kevin'
	result = assert_success(
		url + 'course1/challenge/Lawrence?list_only=true')
	assert len(result['files']) == 1
	assert list(result['files'][0]) == ['path']
	assert result['files'][0]['path'] == 'a'
	user = 'Eric'
	assert_fail(url + 'course2/assignment2a/Eric',
				msg='Permission denied (not course instructor)')

def test_upload_feedback() :
	url = '/api/feedback/'
	global user
	user = 'Kevin'
	data = {'files': json.dumps([{'path': 'a', 'content': 'amtsCg=='},
									{'path': 'b', 'content': 'amtsCg=='}]),
			'timestamp': '2020-01-01 00:00:00.000000 '}
	assert_fail(url + 'jkl/challenge/st', method=POST, data=data,
				msg='Course not found')
	assert_fail(url + 'course1/challenges/st', method=POST, data=data,
				msg='Assignment not found')
	assert_fail(url + 'course1/challenge/st', method=POST, data=data,
				msg='Student not found')
	assert_success(url + 'course1/challenge/Lawrence',
					method=POST, data=data)
	data['files'] = json.dumps([{'path': 'c', 'content': 'amtsCf=='}])
	assert_success(url + 'course1/challenge/Lawrence',
					method=POST, data=data)
	assert_fail(url + 'course1/challenge/Lawrence', method=POST, data={},
				msg='Please supply timestamp')
	assert_fail(url + 'course1/challenge/Lawrence', method=POST,
				data={'timestamp': 'a'}, msg='Time format incorrect')
	user = 'Abigail'
	assert_fail(url + 'course2/assignment2a/Eric', method=POST, data=data,
				msg='Submission not found')
	assert_fail(url + 'course2/assignment2a/Eric', method=POST,
				data={'timestamp': data['timestamp']},
				msg='Submission not found')
	user = 'Eric'
	assert_fail(url + 'course2/assignment2a/Eric', method=POST, data=data,
				msg='Permission denied (not course instructor)')

def test_download_feedback() :
	url = '/api/feedback/'
	global user
	user = 'Kevin'
	assert_fail(url + 'jkl/challenge/st', msg='Course not found')
	assert_fail(url + 'course1/challenges/st', msg='Assignment not found')
	assert_fail(url + 'course1/challenge/st', msg='Student not found')
	meta = assert_success('/api/submission/course1/challenge/Lawrence')
	timestamp = meta['timestamp']
	assert_fail(url + 'course1/challenge/Lawrence', params={},
				msg='Please supply timestamp')
	assert_fail(url + 'course1/challenge/Lawrence', params={'timestamp': 'a'},
				msg='Time format incorrect')
	user = 'Eric'
	assert_fail(url + 'course2/assignment2a/Eric',
				params={'timestamp': timestamp}, msg='Submission not found')
	user = 'Kevin'
	feedback = assert_success(url + 'course1/challenge/Lawrence', 
							params={'timestamp': timestamp})
	assert feedback['files'] == []
	# Submit again
	data = {'files': json.dumps([{'path': 'a', 'content': 'amtsDg=='}]),
			'timestamp': timestamp}
	assert_success(url + 'course1/challenge/Lawrence', method=POST, data=data)
	# Fetch again
	feedback = assert_success(url + 'course1/challenge/Lawrence', 
							params={'timestamp': timestamp})
	assert len(feedback['files']) == 1
	assert feedback['files'][0]['path'] == 'a'
	assert feedback['files'][0]['content'].replace('\n', '') == 'amtsDg=='
	# Again, submit again
	data = {'files': json.dumps([{'path': 'a', 'content': 'bmtsDg=='}]),
			'timestamp': timestamp}
	assert_success(url + 'course1/challenge/Lawrence', method=POST, data=data)
	# Again, fetch again
	feedback = assert_success(url + 'course1/challenge/Lawrence',
							params={'timestamp': timestamp})
	assert len(feedback['files']) == 1
	assert feedback['files'][0]['path'] == 'a'
	assert feedback['files'][0]['content'].replace('\n', '') == 'bmtsDg=='
	# Check list_only
	feedback = assert_success(url + 'course1/challenge/Lawrence',
							params={'timestamp': timestamp,
									'list_only': 'true'})
	assert len(feedback['files']) == 1
	assert list(feedback['files'][0]) == ['path']
	assert feedback['files'][0]['path'] == 'a'
	# Permission check
	user = 'Kevin'
	assert_fail(url + 'course1/challenge/Lawrence',
				msg='Please supply timestamp')
	user = 'Abigail'
	assert_fail(url + 'course1/challenge/Lawrence',
				msg='Permission denied (not course instructor)')
	user = 'Lawrence'
	assert_fail(url + 'course1/challenge/Lawrence',
				msg='Please supply timestamp')
	user = 'Eric'
	assert_fail(url + 'course1/challenge/Lawrence',
				msg='Permission denied (not course instructor)')

