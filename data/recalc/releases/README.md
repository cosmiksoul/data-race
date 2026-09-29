# Флагманы и вычисления на обучение: скрипты блока 11

- `build_lists.py` — список флагманов шести лабораторий (`content/data/11-releases.csv`) и промежуточных версий;
- `cadence.py` — число флагманов по годам и медианы интервалов (`content/data/11-cadence.csv`), проверка на разных определениях флагмана;
- `compute.py` — тренд вычислений на обучение по наборам Epoch AI (`content/data/11-compute-trend.csv`, `11-training-compute.csv`, `11-record.csv`).

Скрипты писались в рабочей папке с подпапками `in/` (наборы Epoch AI «Data on AI models» от 28.09.2026, CC BY 4.0: `epoch_frontier_ai_models.csv`, `epoch_notable_ai_models.csv`, `epoch_all_ai_models.csv`) и `out/`. Для повторного запуска скачайте наборы с https://epoch.ai/data/ai-models в `in/` и поправьте пути в начале скриптов.
