## Trabalho Sistemas Distribuídos - File Transfer gRPC

Código fonte referente ao trabalho da disciplina de Sistemas Distribuídos T01-2024-1

### Ambiente
O projeto foi desenvolvido em um ambiente `Linux`, mais especificamente o `Ubuntu 22.04` rodando no `WSL2`

### Dependências
- `grpc`
- `grpc-tools`

### Pacotes e execução
Na raíz do projeto, execute as seguintes linhas de comando para:

Identificar e instalar os pacotes
```
pip install -e .
```

Executar o servidor
```
python src/server.py -port <porta>
```


Executar o cliente
```
python src/client.py -port <porta>
```
