from datetime import datetime
from flask import Flask, render_template, Response,jsonify, request
from matplotlib.dates import relativedelta
import pandas as pd  
from camera import VideoCamera
from detection import ObjectDetector
import cv2
import mysql.connector

app = Flask(__name__)
detector = ObjectDetector()

def gen_frames(camera):
    while True:
        try:
            success, frame = camera.get_frame()
            if not success:
                break
                
            # Realizar detecção e tracking
            results = detector.detect(frame)
            frame = detector.process_detections(frame, results)
            
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        except Exception as e:
            print(f"Error in video feed: {e}")
            break

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(VideoCamera()),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/registros')
def get_registros():
    try:
        conn = mysql.connector.connect(**detector.db.config)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                id,
                data_hora_entrada,
                CASE 
                    WHEN data_hora_saida IS NULL THEN 'Em andamento'
                    ELSE data_hora_saida
                END as saida_formatada,
                CASE
                    WHEN duracao_segundos IS NULL THEN '--'
                    ELSE CONCAT(
                        FLOOR(duracao_segundos / 60), 
                        'm ', 
                        LPAD(duracao_segundos % 60, 2, '0'), 
                        's'
                    )
                END as duracao_formatada
            FROM registros_pessoas
            ORDER BY id DESC
            LIMIT 10
        """)
        
        registros = cursor.fetchall()
        return jsonify({'data': registros})
    
    except Exception as e:
        print(f"Erro ao buscar registros: {e}")
        return jsonify({'data': [], 'error': str(e)}), 500
    
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/entradas-por-mes')
def get_entradas_por_mes():
    conn = None
    cursor = None
    try:
        # Estabelece conexão com o banco de dados (usando as mesmas credenciais do Database)
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='root',
            database='controle_acesso'
        )
        cursor = conn.cursor(dictionary=True)
        
        # Consulta para obter o período total
        cursor.execute("""
            SELECT 
                DATE_FORMAT(MIN(data_hora_entrada), '%Y-%m-01') as primeiro_mes,
                DATE_FORMAT(MAX(data_hora_entrada), '%Y-%m-01') as ultimo_mes
            FROM registros_pessoas
            WHERE data_hora_entrada IS NOT NULL
        """)
        periodo = cursor.fetchone()
        
        # Se não houver registros, retorna estrutura vazia
        if not periodo or not periodo['primeiro_mes']:
            return jsonify({
                'status': 'success',
                'data': {
                    'labels': [],
                    'values': []
                }
            })
        
        # Gera todos os meses no intervalo
        meses = []
        current = datetime.strptime(periodo['primeiro_mes'], '%Y-%m-%d')
        end = datetime.strptime(periodo['ultimo_mes'], '%Y-%m-%d')
        
        while current <= end:
            meses.append(current.strftime('%Y-%m'))
            current = current + relativedelta(months=+1)
        
        # Consulta os dados agrupados por mês
        cursor.execute("""
            SELECT 
                DATE_FORMAT(data_hora_entrada, '%Y-%m') as mes,
                COUNT(*) as total
            FROM registros_pessoas
            GROUP BY mes
            ORDER BY mes
        """)
        dados_existentes = {row['mes']: row['total'] for row in cursor.fetchall()}
        
        # Preenche com zero os meses sem registros
        resultado = []
        for mes in meses:
            resultado.append({
                'mes': mes,
                'total': dados_existentes.get(mes, 0)
            })
        
        return jsonify({
            'status': 'success',
            'data': {
                'labels': [item['mes'] for item in resultado],
                'values': [item['total'] for item in resultado]
            }
        })
        
    except Exception as e:
        print(f"Erro na API: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': 'Erro interno no servidor',
            'details': str(e)
        }), 500
        
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route('/api/pessoas-detectadas')
def get_pessoas_detectadas():
    try:
        # Acessa diretamente o dicionário de registros ativos do detector
        pessoas_detectadas = len(detector.current_registros) > 0
        return jsonify({
            'status': 'success',
            'pessoas_detectadas': pessoas_detectadas,
            'contagem': len(detector.current_registros)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/registro-esp32', methods=['POST'])
def registro_esp32():
    try:
        data = request.json
        tipo = data.get('tipo')
        
        # Verifica se há pessoas detectadas pela câmera
        pessoas_detectadas = len(detector.current_registros) > 0
        
        if tipo == "sinal_interrompido" and pessoas_detectadas:
            # Apenas registra no banco existente se a câmera também detectar
            for track_id, registro_id in detector.current_registros.items():
                detector.db.registrar_saida(registro_id)
            
            return jsonify({
                'status': 'success',
                'message': 'Evento confirmado pela câmera',
                'pessoas_detectadas': pessoas_detectadas
            })
        
        return jsonify({
            'status': 'success',
            'message': 'Evento recebido (não confirmado)',
            'pessoas_detectadas': pessoas_detectadas
        })
            
    except Exception as e:
        print(f"Erro no registro ESP32: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)