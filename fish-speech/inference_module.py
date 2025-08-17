import torch
from pathlib import Path
import numpy as np
from fish_speech.inference_engine import TTSInferenceEngine
from fish_speech.models.text2semantic.inference import launch_thread_safe_queue
from fish_speech.models.vqgan.inference import load_model as load_decoder_model
from fish_speech.utils.schema import ServeTTSRequest, ServeReferenceAudio

# checkpoints/fish-speech-1.5 -> checkpoints/fish-speech-1.5-yth-lora
def init_engine(
    #llama_checkpoint_path="checkpoints/fish-speech-1.5",
    llama_checkpoint_path="checkpoints/fish-speech-1.5-yth-lora-new-step_000009250",
    decoder_checkpoint_path="checkpoints/fish-speech-1.5/firefly-gan-vq-fsq-8x1024-21hz-generator.pth",
    #decoder_checkpoint_path="checkpoints/fish-speech-1.5-yth-lora-8000/model.pth",
    decoder_config_name="firefly_gan_vq",
    device="cuda",
    half=False,
    compile=False
):
    precision = torch.half if half else torch.bfloat16

    if torch.backends.mps.is_available():
        device = "mps"
    elif not torch.cuda.is_available():
        device = "cpu"

    
    
    llama_queue = launch_thread_safe_queue(
        checkpoint_path=Path(llama_checkpoint_path),
        device=device,
        precision=precision,
        compile=compile
    )

    decoder_model = load_decoder_model(
        config_name=decoder_config_name,
        checkpoint_path=Path(decoder_checkpoint_path),
        device=device
    )

    return TTSInferenceEngine(
        llama_queue=llama_queue,
        decoder_model=decoder_model,
        compile=compile,
        precision=precision
    )


def run_tts(engine, input_text, prompt_audio_path=None, prompt_text=""):
    references = []
    if prompt_audio_path:
        with open(prompt_audio_path, "rb") as f:
            audio_bytes = f.read()
        references = [ServeReferenceAudio(audio=audio_bytes, text=prompt_text)]

    request = ServeTTSRequest(
        text=input_text,
        reference_id=None,
        references=references,
        max_new_tokens=0,
        chunk_length=200,
        top_p=0.7,
        repetition_penalty=1.2,
        temperature=0.7,
        seed=0,
        use_memory_cache="on",
        format="wav"
    )

    for result in engine.inference(request):
        if result.code == "final":
            return result.audio  # -> (sample_rate: int, waveform: np.ndarray)
        elif result.code == "error":
            raise RuntimeError(result.error)

    raise RuntimeError("No audio generated.")