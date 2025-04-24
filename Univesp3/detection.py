from datetime import datetime
from ultralytics import YOLO
import cv2
import numpy as np
from database import Database
from collections import defaultdict
import os

class ObjectDetector:
    def __init__(self):
        self.model = YOLO('yolov8n.pt')
        self.class_names = self.model.names
        self.person_class_id = 0
        self.db = Database()
        self.current_registros = {}
        self.track_history = defaultdict(list)
        
        # Verifica se o arquivo de tracker existe
        self.tracker_config = 'tracker.yaml'
        if not os.path.exists(self.tracker_config):
            self._create_default_tracker_file()

    def _create_default_tracker_file(self):
        """Cria arquivo de configuração padrão se não existir"""
        default_config = """
        tracker_type: botsort
        track_high_thresh: 0.5
        track_low_thresh: 0.1
        new_track_thresh: 0.6
        match_thresh: 0.8
        frame_rate: 30
        """
        with open(self.tracker_config, 'w') as f:
            f.write(default_config)

    def detect(self, frame):
        try:
            results = self.model.track(
                source=frame,
                persist=True,
                verbose=False,
                classes=[self.person_class_id],
                tracker="botsort.yaml",  # Usa configurações embutidas
                imgsz=640
            )
            return results[0] if results else None
        except Exception as e:
            print(f"Erro durante detecção: {str(e)}")
            return None

    def process_detections(self, frame, results):
        if results is None:
            return frame
            
        registros_anteriores = len(self.current_registros)
        active_tracks = set()
        
        if results.boxes is not None and results.boxes.id is not None:
            boxes = results.boxes.xyxy.cpu().numpy()
            track_ids = results.boxes.id.cpu().numpy().astype(int)
            confidences = results.boxes.conf.cpu().numpy()
            
            for box, track_id, conf in zip(boxes, track_ids, confidences):
                # Desenha o retângulo e ID de tracking
                x1, y1, x2, y2 = map(int, box)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"ID: {track_id} ({conf:.2f})", 
                            (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 
                            0.6, (0, 255, 0), 2)
                
                active_tracks.add(track_id)
                if track_id not in self.current_registros:
                    self.current_registros[track_id] = {
                        'id': self.db.registrar_entrada(),
                        'first_seen': datetime.now()
                    }
        
        # Verifica saídas
        for track_id in list(self.current_registros.keys()):
            if track_id not in active_tracks:
                self.db.registrar_saida(self.current_registros[track_id]['id'])
                del self.current_registros[track_id]
        
        return frame
    
    def get_active_registros(self):
        """Retorna os registros ativos de pessoas detectadas"""
        return self.current_registros