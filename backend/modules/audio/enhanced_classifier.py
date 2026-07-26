import logging
import numpy as np
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from collections import deque
import struct

logger = logging.getLogger(__name__)


@dataclass
class SoundClassifyResult:
    sound_type: str
    sound_label: str
    confidence: float
    danger_score: float
    
    volume_db: float = 0.0
    frequency_peak: float = 0.0
    direction: Optional[str] = None
    urgency: int = 0


SOUND_TYPES = {
    "car_horn": {
        "label": "汽车鸣笛",
        "danger_score": 0.85,
        "urgency": 3,
        "keywords": ["喇叭", "鸣笛", "滴滴", "嘟嘟", "按喇叭", "车喇叭", "horn"],
        "freq_range": (400, 500),
        "duration_range": (0.5, 3.0),
    },
    "brake_sound": {
        "label": "刹车声",
        "danger_score": 0.95,
        "urgency": 3,
        "keywords": ["刹车", "急刹", "吱", "摩擦", "brake", "急停"],
        "freq_range": (1000, 4000),
        "duration_range": (0.3, 2.0),
    },
    "siren": {
        "label": "警笛",
        "danger_score": 0.9,
        "urgency": 3,
        "keywords": ["警笛", "救护车", "消防车", "警车", "呜", "siren", "ambulance"],
        "freq_range": (500, 1800),
        "duration_range": (1.0, 5.0),
    },
    "engine_accelerating": {
        "label": "引擎加速声",
        "danger_score": 0.75,
        "urgency": 2,
        "keywords": ["引擎", "发动机", "轰鸣", "油门", "加速", "马达"],
        "freq_range": (100, 300),
        "duration_range": (1.0, 5.0),
    },
    "electric_vehicle": {
        "label": "电动车",
        "danger_score": 0.8,
        "urgency": 2,
        "keywords": ["电动车", "电瓶车", "外卖", "电车"],
        "freq_range": (300, 800),
        "duration_range": (0.5, 3.0),
    },
    "bike_bell": {
        "label": "自行车铃",
        "danger_score": 0.45,
        "urgency": 1,
        "keywords": ["铃铛", "自行车", "叮", "车铃"],
        "freq_range": (2000, 4000),
        "duration_range": (0.2, 1.0),
    },
    "human_shout": {
        "label": "人喊叫",
        "danger_score": 0.7,
        "urgency": 2,
        "keywords": ["小心", "让开", "危险", "注意", "闪开", "快跑", "救命", "喂"],
        "freq_range": (200, 1000),
        "duration_range": (0.5, 3.0),
    },
    "footsteps": {
        "label": "脚步声",
        "danger_score": 0.3,
        "urgency": 0,
        "keywords": ["脚步", "走路", "跑步"],
        "freq_range": (50, 200),
        "duration_range": (1.0, 10.0),
    },
    "construction": {
        "label": "施工噪音",
        "danger_score": 0.6,
        "urgency": 1,
        "keywords": ["施工", "工地", "打桩", "钻孔", "电钻"],
        "freq_range": (100, 2000),
        "duration_range": (5.0, 60.0),
    },
    "rain": {
        "label": "雨声",
        "danger_score": 0.2,
        "urgency": 0,
        "keywords": ["雨", "下雨", "雨声"],
        "freq_range": (1000, 10000),
        "duration_range": (10.0, 600.0),
    },
}


class EnhancedSoundClassifier:
    def __init__(self, history_size: int = 10):
        self.history = deque(maxlen=history_size)
        self.yamnet_model = None
        self._try_load_yamnet()
    
    def _try_load_yamnet(self):
        try:
            import tensorflow_hub as hub
            self.yamnet_model = hub.load('https://tfhub.dev/google/yamnet/1')
            logger.info("✅ YAMNet模型加载成功")
        except Exception as e:
            logger.info(f"⚪ YAMNet未加载: {e}")
            self.yamnet_model = None
    
    def classify(
        self, 
        audio_data: bytes = None,
        asr_text: str = None,
        sample_rate: int = 16000
    ) -> Optional[SoundClassifyResult]:
        results = []
        
        if asr_text:
            keyword_result = self._classify_by_keywords(asr_text)
            if keyword_result:
                results.append(("keyword", keyword_result, 1.0))
        
        if audio_data:
            freq_result = self._classify_by_frequency(audio_data, sample_rate)
            if freq_result:
                results.append(("frequency", freq_result, 0.6))
        
        if audio_data and self.yamnet_model:
            yamnet_result = self._classify_by_yamnet(audio_data, sample_rate)
            if yamnet_result:
                results.append(("yamnet", yamnet_result, 0.9))
        
        if not results:
            return None
        
        final_result = self._fuse_results(results)
        
        self.history.append(final_result)
        smoothed = self._temporal_smooth()
        
        return smoothed
    
    def _classify_by_keywords(self, text: str) -> Optional[SoundClassifyResult]:
        text_lower = text.lower()
        
        best_match = None
        best_score = 0
        
        for sound_type, info in SOUND_TYPES.items():
            match_count = 0
            for keyword in info["keywords"]:
                if keyword in text_lower:
                    match_count += 1
            
            if match_count > 0:
                score = match_count / len(info["keywords"])
                if score > best_score:
                    best_score = score
                    best_match = SoundClassifyResult(
                        sound_type=sound_type,
                        sound_label=info["label"],
                        confidence=min(score * 2.0, 1.0),
                        danger_score=info["danger_score"],
                        urgency=info["urgency"]
                    )
        
        return best_match
    
    def _classify_by_frequency(
        self, 
        audio_data: bytes, 
        sample_rate: int
    ) -> Optional[SoundClassifyResult]:
        try:
            samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            if len(samples) < 1024:
                return None
            
            fft = np.fft.rfft(samples)
            magnitude = np.abs(fft)
            freqs = np.fft.rfftfreq(len(samples), 1.0 / sample_rate)
            
            peak_idx = np.argmax(magnitude)
            peak_freq = freqs[peak_idx]
            
            logger.debug(f"主频率: {peak_freq:.1f} Hz")
            
            best_match = None
            best_score = 0
            
            for sound_type, info in SOUND_TYPES.items():
                freq_range = info.get("freq_range")
                if not freq_range:
                    continue
                
                if freq_range[0] <= peak_freq <= freq_range[1]:
                    center = (freq_range[0] + freq_range[1]) / 2
                    distance = abs(peak_freq - center)
                    bandwidth = (freq_range[1] - freq_range[0]) / 2
                    
                    score = 1.0 - (distance / bandwidth)
                    score = max(0, score)
                    
                    if score > best_score:
                        best_score = score
                        best_match = SoundClassifyResult(
                            sound_type=sound_type,
                            sound_label=info["label"],
                            confidence=score,
                            danger_score=info["danger_score"],
                            urgency=info["urgency"],
                            frequency_peak=peak_freq
                        )
            
            return best_match
            
        except Exception as e:
            logger.error(f"频谱分析异常: {e}")
            return None
    
    def _classify_by_yamnet(
        self, 
        audio_data: bytes, 
        sample_rate: int
    ) -> Optional[SoundClassifyResult]:
        if self.yamnet_model is None:
            return None
        
        try:
            import numpy as np
            import tensorflow as tf
            
            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            if sample_rate != 16000:
                ratio = 16000 / sample_rate
                new_length = int(len(audio_np) * ratio)
                audio_np = np.interp(
                    np.linspace(0, len(audio_np), new_length),
                    np.arange(len(audio_np)),
                    audio_np
                )
            
            scores, embeddings, spectrogram = self.yamnet_model(audio_np)
            
            class_names = self.yamnet_model.class_names.numpy()
            top_idx = scores.numpy().mean(axis=0).argmax()
            top_class = class_names[top_idx].decode('utf-8')
            top_score = float(scores.numpy().mean(axis=0).max())
            
            logger.debug(f"YAMNet: {top_class} ({top_score:.2f})")
            
            mapped = self._map_yamnet_class(top_class, top_score)
            return mapped
            
        except Exception as e:
            logger.error(f"YAMNet分类异常: {e}")
            return None
    
    def _map_yamnet_class(self, yamnet_class: str, confidence: float) -> Optional[SoundClassifyResult]:
        mapping = {
            "Vehicle horn, car horn, honking": "car_horn",
            "Honking": "car_horn",
            "Car horn": "car_horn",
            "Bicycle bell": "bike_bell",
            "Siren": "siren",
            "Ambulance (siren)": "siren",
            "Police car (siren)": "siren",
            "Screaming": "human_shout",
            "Shout": "human_shout",
            "Tire squeal": "brake_sound",
            "Skidding": "brake_sound",
            "Engine": "engine_accelerating",
            "Accelerating, revving, vroom": "engine_accelerating",
        }
        
        our_type = None
        for yamnet_key, mapped_type in mapping.items():
            if yamnet_key.lower() in yamnet_class.lower():
                our_type = mapped_type
                break
        
        if our_type and our_type in SOUND_TYPES:
            info = SOUND_TYPES[our_type]
            return SoundClassifyResult(
                sound_type=our_type,
                sound_label=info["label"],
                confidence=confidence,
                danger_score=info["danger_score"],
                urgency=info["urgency"]
            )
        
        return None
    
    def _fuse_results(self, results: List[Tuple[str, SoundClassifyResult, float]]) -> SoundClassifyResult:
        type_scores = {}
        
        for method, result, weight in results:
            score = result.confidence * weight
            
            if result.sound_type in type_scores:
                type_scores[result.sound_type] += score
            else:
                type_scores[result.sound_type] = score
        
        best_type = max(type_scores, key=type_scores.get)
        best_score = type_scores[best_type]
        
        total_weight = sum(w for _, _, w in results)
        final_confidence = min(best_score / total_weight, 1.0)
        
        info = SOUND_TYPES[best_type]
        
        return SoundClassifyResult(
            sound_type=best_type,
            sound_label=info["label"],
            confidence=final_confidence,
            danger_score=info["danger_score"],
            urgency=info["urgency"]
        )
    
    def _temporal_smooth(self) -> Optional[SoundClassifyResult]:
        if not self.history:
            return None
        
        type_counts = {}
        
        for result in self.history:
            if result.sound_type in type_counts:
                type_counts[result.sound_type] += 1
            else:
                type_counts[result.sound_type] = 1
        
        most_common = max(type_counts, key=type_counts.get)
        count = type_counts[most_common]
        
        if count < 3:
            confidence_factor = count / 3.0
        else:
            confidence_factor = 1.0
        
        for result in reversed(self.history):
            if result.sound_type == most_common:
                result.confidence *= confidence_factor
                return result
        
        return self.history[-1]
    
    def classify_by_volume(self, audio_data: bytes) -> dict:
        try:
            samples = struct.unpack(f"<{len(audio_data)//2}h", audio_data)
            
            if not samples:
                return {"rms": 0, "peak": 0, "is_loud": False, "db": 0}
            
            rms = (sum(s**2 for s in samples) / len(samples)) ** 0.5
            peak = max(abs(s) for s in samples)
            
            rms_normalized = rms / 32768.0
            db = 20 * np.log10(rms_normalized + 1e-10)
            db = max(db, -60)
            
            if db > -10:
                loudness = "very_loud"
                is_loud = True
            elif db > -20:
                loudness = "loud"
                is_loud = True
            elif db > -30:
                loudness = "medium"
                is_loud = False
            else:
                loudness = "quiet"
                is_loud = False
            
            return {
                "rms": round(rms_normalized, 4),
                "peak": round(peak / 32768.0, 4),
                "db": round(db, 1),
                "is_loud": is_loud,
                "loudness": loudness
            }
            
        except Exception as e:
            logger.error(f"音量分析异常: {e}")
            return {"rms": 0, "peak": 0, "is_loud": False, "db": 0}