CREATE TABLE Usuario (
    ID_Usuario INT PRIMARY KEY AUTO_INCREMENT,
    Nome VARCHAR(50) NOT NULL,
    Email VARCHAR(100) UNIQUE NOT NULL,
    Senha_Hash VARCHAR(255) NOT NULL -- Senha deve ser armazenada como hash
);

CREATE TABLE Biblioteca (
    ID_Biblioteca INT PRIMARY KEY AUTO_INCREMENT,
    Nome_Biblioteca VARCHAR(50) NOT NULL,
    ID_Usuario INT NOT NULL,
    FOREIGN KEY (ID_Usuario) REFERENCES Usuario(ID_Usuario) ON DELETE CASCADE
);

CREATE TABLE Diretorio (
    ID_Diretorio INT PRIMARY KEY AUTO_INCREMENT,
    Nome_Diretorio VARCHAR(50) NOT NULL,
    ID_Biblioteca INT NOT NULL,
    FOREIGN KEY (ID_Biblioteca) REFERENCES Biblioteca(ID_Biblioteca) ON DELETE CASCADE
);

CREATE TABLE Tipo_Documento (
    ID_Tipo INT PRIMARY KEY AUTO_INCREMENT,
    Nome_Tipo VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE Tipo_Documento (
    ID_Tipo INT PRIMARY KEY AUTO_INCREMENT,
    Nome_Tipo VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE Documento (
    ID_Documento INT PRIMARY KEY AUTO_INCREMENT,
    Nome_Documento VARCHAR(50) NOT NULL,
    ID_Tipo INT NOT NULL,
    Data_Upload DATE NOT NULL,
    Caminho_Arquivo VARCHAR(255) NOT NULL,
    ID_Diretorio INT NOT NULL,
    FOREIGN KEY (ID_Tipo) REFERENCES Tipo_Documento(ID_Tipo),
    FOREIGN KEY (ID_Diretorio) REFERENCES Diretorio(ID_Diretorio) ON DELETE CASCADE
);

