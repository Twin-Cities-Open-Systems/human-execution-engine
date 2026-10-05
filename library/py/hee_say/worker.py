#!/usr/bin/env python3
"""hee_say worker -- the half of hee-say that needs the speech engine.

Run by tooling/bin/hee-say under the engine's own venv ($HEE_SAY_HOME/venv),
never imported: the engine's dependencies (onnxruntime, numpy, pypdf) are not
on the system python and must not have to be. Standard library plus the venv.

  worker.py synth PLAN.json OUT.wav   synthesize a plan's blocks; print the
                                      second each block starts, as JSON
  worker.py phonemes                  JSON list of texts on stdin -> their phonemes
  worker.py voices                    the engine's voice names, one per line
  worker.py pdftext FILE              a PDF's text, page by page, as JSON
"""
import json
import os
import sys
from pathlib import Path

HOME = Path(os.environ["HEE_SAY_HOME"])


def engine():
    from kokoro_onnx import Kokoro
    return Kokoro(str(HOME / "kokoro-v1.0.onnx"), str(HOME / "voices-v1.0.bin"))


def synth(plan_path, wav_path):
    import numpy as np
    import soundfile as sf
    plan = json.loads(Path(plan_path).read_text())
    kokoro = engine()
    if plan["voice"] not in kokoro.get_voices():
        sys.exit(f"no such voice: {plan['voice']} (hee say voices lists them)")
    rate = 24000
    parts = [np.zeros(int(rate * plan["lead"]), dtype=np.float32)]
    starts, at = [], len(parts[0])
    for text, pause in plan["blocks"]:
        samples, rate = kokoro.create(text, voice=plan["voice"], speed=plan["speed"], lang=plan["lang"])
        gap = np.zeros(int(rate * pause), dtype=np.float32)
        starts.append(round(at / rate, 2))
        at += len(samples) + len(gap)
        parts += [samples, gap]
    sf.write(wav_path, np.concatenate(parts), rate)
    print(json.dumps({"starts": starts, "seconds": round(at / rate, 2)}))


def main(argv):
    if argv[:1] == ["synth"] and len(argv) == 3:
        synth(argv[1], argv[2])
    elif argv == ["phonemes"]:
        lang = os.environ.get("HEE_SAY_LANG", "en-us")
        tok = engine().tokenizer
        print(json.dumps([tok.phonemize(t, lang) for t in json.load(sys.stdin)], ensure_ascii=False))
    elif argv == ["voices"]:
        print("\n".join(sorted(engine().get_voices())))
    elif argv[:1] == ["pdftext"] and len(argv) == 2:
        from pypdf import PdfReader
        print(json.dumps([page.extract_text() for page in PdfReader(argv[1]).pages]))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
