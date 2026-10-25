import time, pathlib, sys
from audio_processor import JobManager, probe_media

sample = pathlib.Path('..\\test_sample.mp3')
if not sample.exists():
    print('Sample file not found')
    sys.exit(1)
info = probe_media(sample)
print('Duration:', info['duration'])
jm = JobManager(pathlib.Path('temp'))
job = jm.create_job('perfjob', sample.name, info['duration'], 0.5, 'mp3')
start = time.time()
jm.process_split_job('perfjob', sample)
print('Processing took', time.time() - start, 'seconds')
