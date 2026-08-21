"""F14 hakemlik EVAL paketi — kalite kanıtı (R-3).

Motorun ürettiği değerlendirmenin (verdict + boyut skorları) İNSAN hakem
değerlendirmesiyle ne kadar uyuştuğunu ÖLÇER. "Stanford kalite" iddiasını
ölçülebilir yapar (master §6 R-3). Stanford kendi aracını ICLR 2025'e karşı
kalibre etti: Spearman 0.42 ≈ insan-insan 0.41.
"""

from __future__ import annotations
