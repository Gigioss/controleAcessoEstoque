import mysql.connector
from mysql.connector import Error
from datetime import datetime

class Database:
    def __init__(self):
        self.config = {
            'host': 'localhost',
            'user': 'root',
            'password': 'root',
            'database': 'controle_acesso'
        }
        self.create_connection()
        self.create_table()

    def create_connection(self):
        try:
            self.connection = mysql.connector.connect(**self.config)
            if self.connection.is_connected():
                print("Conexão ao MySQL estabelecida")
        except Error as e:
            print(f"Erro ao conectar ao MySQL: {e}")

    def create_table(self):
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS registros_pessoas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    data_hora_entrada DATETIME NOT NULL,
                    data_hora_saida DATETIME,
                    duracao_segundos INT
                )
            """)
            print("Tabela verificada/criada com sucesso")
        except Error as e:
            print(f"Erro ao criar tabela: {e}")

    def registrar_entrada(self):
        try:
            cursor = self.connection.cursor()
            query = "INSERT INTO registros_pessoas (data_hora_entrada) VALUES (%s)"
            cursor.execute(query, (datetime.now(),))
            self.connection.commit()
            return cursor.lastrowid
        except Error as e:
            print(f"Erro ao registrar entrada: {e}")
            return None

    def registrar_saida(self, registro_id):
        try:
            cursor = self.connection.cursor()
            
            # Obter a entrada para calcular duração
            cursor.execute("SELECT data_hora_entrada FROM registros_pessoas WHERE id = %s", (registro_id,))
            entrada = cursor.fetchone()[0]
            saida = datetime.now()
            duracao = int((saida - entrada).total_seconds())
            
            # Atualizar registro
            query = """
                UPDATE registros_pessoas 
                SET data_hora_saida = %s, duracao_segundos = %s 
                WHERE id = %s
            """
            cursor.execute(query, (saida, duracao, registro_id))
            self.connection.commit()
            return True
        except Error as e:
            print(f"Erro ao registrar saída: {e}")
            return False

    def __del__(self):
        if hasattr(self, 'connection') and self.connection.is_connected():
            self.connection.close()
            print("Conexão MySQL fechada")

    