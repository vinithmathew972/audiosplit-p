import sys
sys.path.append('d:/audio_split_p/AudioSplit-Pro/backend')
from audio_processor import JobManager
from pathlib import Path
jm = JobManager(Path('d:/audio_split_p/AudioSplit-Pro/backend/temp'))
job = jm.create_job('rel_test','test_sample.mp3',75.0,0.5,'mp3')
print('Job created')
try:
    jm.process_split_job('rel_test', Path('test_sample.mp3'))
    print('Completed')
except Exception as e:
    print('Exception:', e)
print('Job data:', jm.get_job('rel_test'))
