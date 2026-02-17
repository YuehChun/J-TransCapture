# faster-whisper vs mlx-whisper 技術比較

## 背景

兩者都是 OpenAI Whisper 語音辨識模型的替代推理引擎，目標是比原版 Whisper 更快、更省記憶體。它們針對不同硬體架構做了各自的底層優化。

## 核心差異

| | faster-whisper | mlx-whisper |
|---|---|---|
| **底層引擎** | CTranslate2 (C++) | Apple MLX (Metal) |
| **硬體加速** | NVIDIA CUDA GPU / CPU | Apple Silicon GPU (Metal) |
| **量化推理** | INT8 / FP16 | FP16 (Metal native) |
| **目標平台** | Linux / Windows (NVIDIA GPU)、任意 CPU | macOS (Apple Silicon only) |
| **模型格式** | CTranslate2 格式 | MLX 格式 (HuggingFace Hub) |
| **Python API** | 自有 API（generator 迭代） | 類似原版 Whisper API（dict 回傳） |
| **GPU 支援** | NVIDIA only（CUDA） | Apple only（Metal） |
| **CPU fallback** | 有（INT8 量化） | 無（需要 Apple Silicon） |

## 為什麼會有兩個 Library？

### faster-whisper 的誕生

OpenAI 原版 Whisper 用 PyTorch 推理，速度慢、記憶體用量大。[SYSTRAN](https://github.com/SYSTRAN) 團隊用 **CTranslate2**（一個專為 Transformer 優化的 C++ 推理引擎）重新實作了 Whisper，達成：

- 比原版快 **4 倍**
- 記憶體減少約 **50%**
- 支援 INT8 量化，即使沒有 GPU 也能在 CPU 上高效運行

但 CTranslate2 的 GPU 支援**只有 NVIDIA CUDA**，Apple Silicon 的 GPU 完全用不到，只能跑 CPU。

### mlx-whisper 的誕生

Apple 在 2023 年底發布了 **MLX**，一個專為 Apple Silicon 設計的機器學習框架，類似 PyTorch 但直接用 Metal API 驅動 GPU。社群隨後將 Whisper 移植到 MLX 上，讓 Mac 用戶可以：

- 直接使用 Apple Silicon 的 **GPU + Neural Engine**
- 不需要 NVIDIA 顯卡
- 不需要 CUDA、cuDNN 等依賴

## 架構對比

```
faster-whisper:
  Python API → CTranslate2 (C++) → CUDA / CPU
                                     ↓
                              NVIDIA GPU 或 CPU INT8

mlx-whisper:
  Python API → MLX Framework → Metal API
                                  ↓
                          Apple Silicon GPU
```

## 在 Mac 上的差異

| 場景 | faster-whisper | mlx-whisper |
|------|---------------|-------------|
| **實際使用的硬體** | CPU only (INT8) | GPU (Metal) |
| **GPU 利用率** | 0%（無法使用 Apple GPU） | 100% |
| **預估速度（large-v3）** | ~0.5x 即時速率 | ~1.5-2x 即時速率 |
| **記憶體佔用** | 較低（INT8 量化） | 較高（FP16） |

## 結論

- **有 NVIDIA GPU** → 用 `faster-whisper`（CUDA 加速最成熟）
- **Mac (Apple Silicon)** → 用 `mlx-whisper`（唯一能用 GPU 的選擇）
- 兩者的轉錄品質相同（都是同一個 Whisper large-v3 模型權重，只是推理引擎不同）
