import sys
sys.path.append('d:/audio_split_p/AudioSplit-Pro/backend')
from audio_processor import JobManager
from pathlib import Path
jm = JobManager(Path('d:/audio_split_p/AudioSplit-Pro/backend/temp'))
job = jm.create_job('debug_job','test_sample.mp3',75.0,0.5,'mp3')
try:
    jm.process_split_job('debug_job', Path('d:/audio_split_p/AudioSplit-Pro/test_sample.mp3'))
    print('Job completed')
    print('Job data:', jm.get_job('debug_job'))
except Exception as e:
    print('Exception:', e)
