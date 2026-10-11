# source me: CUDA 12 cuBLAS + cuDNN 9 for CTranslate2 (faster-whisper) on the GPU host.
# Installed outside .venv (uv sync would remove them): uv pip install --target .cuda-libs nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"
_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export LD_LIBRARY_PATH="$_root/.cuda-libs/nvidia/cublas/lib:$_root/.cuda-libs/nvidia/cudnn/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PATH="$HOME/.local/bin:$PATH"
