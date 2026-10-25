import pathlib, time
from audio_processor import JobManager, probe_media
sample = pathlib.Path('..\\test_sample.mp3')
info = probe_media(sample)
jm = JobManager(pathlib.Path('temp_wav'))
job = jm.create_job('wavjob', sample.name, info['duration'], 0.5, 'wav')
start = time.time()
jm.process_split_job('wavjob', sample)
print('Processing wav (re-encode) took', time.time() - start, 'seconds')
