import os
from typing import Optional

class EmailConfig:
    """Configuration class for email settings"""
    
    # Email server settings
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    
    # Email credentials (use environment variables for security)
    EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS', 'your-app-email@gmail.com')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', 'your-app-password')
    
    # Email content settings
    FROM_NAME = os.getenv('FROM_NAME', 'PDF Viewer App')
    
    # Development settings
    DEVELOPMENT_MODE = os.getenv('DEVELOPMENT_MODE', 'True').lower() == 'true'
    
    @classmethod
    def is_configured(cls) -> bool:
        """Check if email is properly configured"""
        return (
            cls.EMAIL_ADDRESS != 'your-app-email@gmail.com' and
            cls.EMAIL_PASSWORD != 'your-app-password' and
            cls.EMAIL_ADDRESS and
            cls.EMAIL_PASSWORD
        )
    
    @classmethod
    def get_reset_email_template(cls, token: str, user_email: str) -> dict:
        """Get email template for password reset"""
        
        # In production, you would use a proper domain
        reset_link = f"http://localhost:8000/reset-password?token={token}"
        
        subject = "Recuperação de Senha - PDF Viewer"
        
        # HTML template
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Recuperação de Senha</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #f4f4f4; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .button {{ 
                    display: inline-block; 
                    padding: 12px 24px; 
                    background-color: #007bff; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 4px; 
                    margin: 10px 0;
                }}
                .token {{ 
                    background-color: #f8f9fa; 
                    border: 1px solid #dee2e6; 
                    padding: 10px; 
                    font-family: monospace; 
                    word-break: break-all;
                }}
                .footer {{ 
                    margin-top: 30px; 
                    padding-top: 20px; 
                    border-top: 1px solid #eee; 
                    color: #666; 
                    font-size: 0.9em;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Recuperação de Senha</h1>
                </div>
                <div class="content">
                    <p>Olá,</p>
                    <p>Você solicitou a recuperação de senha para sua conta no OpenBookReader App.</p>
                    
                    <p>Para redefinir sua senha, clique no botão abaixo:</p>
                    
                    <p style="text-align: center;">
                        <a href="{reset_link}" class="button">Redefinir Senha</a>
                    </p>
                    
                    <p>Ou copie e cole o seguinte token no aplicativo:</p>
                    <div class="token">{token}</div>
                    
                    <p><strong>Este link expira em 1 hora.</strong></p>
                    
                    <p>Se você não solicitou esta recuperação, ignore este email. Sua senha permanecerá inalterada.</p>
                    
                    <div class="footer">
                        <p>
                            Atenciosamente,<br>
                            Equipe OpenBookReader App
                        </p>
                        <p style="font-size: 0.8em; color: #999;">
                            Este é um email automático, não responda a esta mensagem.
                        </p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        text_body = f"""
        Recuperação de Senha - OBR (OpenBookReader)
        
        Olá,
        
        Você solicitou a recuperação de senha para sua conta.
        
        Para redefinir sua senha, use o seguinte token no aplicativo:
        {token}
        
        Ou acesse o link: {reset_link}
        
        Este token expira em 1 hora.
        
        Se você não solicitou esta recuperação, ignore este email.
        
        Atenciosamente,
        Equipe OBR (OpenBookReader)
        """
        
        return {
            'subject': subject,
            'html_body': html_body,
            'text_body': text_body,
            'reset_link': reset_link
        }


# Instructions for setting up email in production
EMAIL_SETUP_INSTRUCTIONS = """
CONFIGURAÇÃO DE EMAIL PARA PRODUÇÃO

1. Para Gmail:
   - Ative a verificação em duas etapas
   - Gere uma senha de aplicativo específica
   - Use essa senha de aplicativo, não sua senha normal

2. Variáveis de ambiente necessárias:
   export EMAIL_ADDRESS="seu-email@gmail.com"
   export EMAIL_PASSWORD="sua-senha-de-aplicativo"
   export SMTP_SERVER="smtp.gmail.com"
   export SMTP_PORT="587"
   export FROM_NAME="Nome da Sua Aplicação"
   export DEVELOPMENT_MODE="False"

3. Para outros provedores:
   - Outlook/Hotmail: smtp.live.com (porta 587)
   - Yahoo: smtp.mail.yahoo.com (porta 587)
   - Outros: consulte a documentação do provedor

4. Segurança:
   - NUNCA coloque credenciais diretamente no código
   - Use sempre variáveis de ambiente
   - Considere usar serviços como SendGrid, AWS SES, etc. para produção

5. Teste local:
   - Mantenha DEVELOPMENT_MODE=True para simular envios
   - Os tokens serão exibidos no console para testes
"""


def print_setup_instructions():
    """Print email setup instructions"""
    print(EMAIL_SETUP_INSTRUCTIONS)


if __name__ == "__main__":
    print_setup_instructions()
    
    # Test email configuration
    config = EmailConfig()
    print(f"\nConfiguração atual:")
    print(f"SMTP Server: {config.SMTP_SERVER}:{config.SMTP_PORT}")
    print(f"Email configurado: {'Sim' if config.is_configured() else 'Não'}")
    print(f"Modo desenvolvimento: {'Sim' if config.DEVELOPMENT_MODE else 'Não'}")