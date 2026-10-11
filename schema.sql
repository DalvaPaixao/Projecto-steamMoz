-- ============================================================
-- Schema da base de dados — Sistema de Cadastro de Funcionários
-- com Reconhecimento Facial (Stemmoz)
--
-- Como usar (XAMPP / phpMyAdmin):
--   1. Abre o phpMyAdmin (http://localhost/phpmyadmin)
--   2. Clica no separador "SQL"
--   3. Cola todo este ficheiro e clica em "Executar"
-- ============================================================

CREATE DATABASE IF NOT EXISTS stemmoz_rh
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE stemmoz_rh;

CREATE TABLE IF NOT EXISTS funcionarios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  codigo VARCHAR(20) NOT NULL UNIQUE,
  nome VARCHAR(150) NOT NULL,
  departamento VARCHAR(100) NOT NULL,

  -- caminhos das imagens guardadas em disco (pasta /uploads)
  foto_bi_path VARCHAR(255) NOT NULL,
  foto_facial_path VARCHAR(255) NOT NULL,

  -- vector de características faciais (128 dimensões), gerado pelo
  -- modelo Dlib/face_recognition a partir da foto facial frontal.
  -- Guardado em formato JSON (lista de 128 números decimais).
  -- É este vector — e não a fotografia — que é usado nas comparações
  -- futuras de reconhecimento facial.
  caracteristicas_faciais TEXT NOT NULL,

  data_cadastro DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Utilizadores que podem entrar no sistema (login). A senha fica guardada
-- cifrada (hash), nunca em texto. O administrador é criado pelo backend, a
-- partir de ADMIN_USER e ADMIN_PASSWORD no ficheiro .env.
CREATE TABLE IF NOT EXISTS utilizadores (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nome_utilizador VARCHAR(100) NOT NULL UNIQUE,
  nome_exibicao VARCHAR(150) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Presenças: no máximo UMA entrada e UMA saída por funcionário por dia
-- (a chave única uq_funcionario_dia_tipo garante-o).
CREATE TABLE IF NOT EXISTS presencas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  funcionario_id INT NOT NULL,
  tipo VARCHAR(10) NOT NULL,          -- 'entrada' ou 'saida'
  data_hora DATETIME NOT NULL,
  data_dia DATE NOT NULL,
  distancia FLOAT NULL,               -- distância facial medida (para revisão)
  UNIQUE KEY uq_funcionario_dia_tipo (funcionario_id, data_dia, tipo),
  INDEX idx_data_dia (data_dia),
  FOREIGN KEY (funcionario_id) REFERENCES funcionarios(id) ON DELETE CASCADE
);