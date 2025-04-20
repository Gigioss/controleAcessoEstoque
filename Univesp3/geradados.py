import csv
import random
from datetime import datetime, timedelta
import pandas as pd

# Configurações
start_date = datetime(2025, 1, 1)
end_date = datetime(2025, 4, 30)
output_file = 'registros_pessoas.csv'

def generate_records():
    current_id = 1
    records = []
    
    # Cria range de datas
    date_range = pd.date_range(start_date, end_date)
    
    for single_date in date_range:
        # Gera entre 40 e 60 registros por dia
        num_registros = random.randint(40, 60)
        
        for _ in range(num_registros):
            # Gera horário de entrada aleatório no dia
            entrada = single_date.replace(
                hour=random.randint(0, 23),
                minute=random.randint(0, 59),
                second=random.randint(0, 59)
            )
            
            # Gera duração entre 30 segundos e 12 horas
            duracao = random.randint(30, 43200)
            saida = entrada + timedelta(seconds=duracao)
            
            records.append({
                'id': current_id,
                'data_hora_entrada': entrada.strftime('%Y-%m-%d %H:%M:%S'),
                'data_hora_saida': saida.strftime('%Y-%m-%d %H:%M:%S'),
                'duracao_segundos': duracao
            })
            current_id += 1
    
    return records

# Gerar dados
dados = generate_records()

# Escrever CSV
with open(output_file, 'w', newline='') as csvfile:
    fieldnames = ['id', 'data_hora_entrada', 'data_hora_saida', 'duracao_segundos']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    
    writer.writeheader()
    for row in dados:
        writer.writerow(row)

print(f"Arquivo {output_file} gerado com {len(dados)} registros")