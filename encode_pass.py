from urllib.parse import quote_plus

# COLOQUE SUA SENHA EXATA AQUI DENTRO DAS ASPAS
original_password = "123456"

encoded_password = quote_plus(original_password)

print("\n======================================================")
print(f"Sua senha original: {original_password}")
print(f"SUA NOVA SENHA (CODIFICADA): {encoded_password}")
print("======================================================\n")
print("Copie a senha codificada e use-a no seu arquivo .env")