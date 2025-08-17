from fastapi import FastAPI, Request
from inference_module import init_engine, run_tts
from scipy.io.wavfile import write as write_wav
import numpy as np
import os

app = FastAPI()
engine = init_engine()

@app.post("/infer")
async def infer(request: Request):
    data = await request.json()
    text = data["text"]
    reference_wav = data["reference_wav"]
    prompt_text = data.get("prompt_text", "")
    
    input_path = f"/app/input_wav/{reference_wav}"
    output_path = f"/app/output_wav/{reference_wav}"

    try:
        sample_rate, waveform = run_tts(engine, text, input_path, prompt_text)
        waveform_int16 = (waveform * 32767).astype(np.int16)
        write_wav(output_path, sample_rate, waveform_int16)
        return {"status": "success", "output_wav": reference_wav}
    except Exception as e:
        return {"status": "error", "message": str(e)}
