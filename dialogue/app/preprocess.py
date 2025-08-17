import os
import subprocess
from pathlib import Path
def preprocess_wav_file(input_path: str, output_path: str, sample_rate: int = 16000):
    """
    FFmpeg를 이용해 단일 WAV 파일을 지정한 경로로 전처리(리샘플링, 모노, PCM)합니다.
    - input_path: 원본 WAV 파일 경로
    - output_path: 전처리된 WAV 파일 경로
    - sample_rate: 리샘플링할 샘플레이트 (기본 16000Hz)
    """
    command = [
        "ffmpeg",
        "-y",                     # 덮어쓰기 허용
        "-i", input_path,         # 입력 파일
        "-ar", str(sample_rate),  # 리샘플링 (예: 16000Hz)
        "-ac", "1",               # 모노 채널로 변환
        "-acodec", "pcm_s16le",   # 16-bit PCM
        output_path
    ]
    # FFmpeg 실행
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_path