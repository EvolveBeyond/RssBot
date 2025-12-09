# Security Policy

## Supported Versions

We actively maintain and provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please send security-related reports to: **security@rssbot.com**

### What to Include

Please include the following information in your report:

- **Description** of the vulnerability
- **Steps to reproduce** the issue
- **Potential impact** and attack scenarios
- **Suggested fix** or mitigation (if known)
- **Your contact information** for follow-up

### Response Timeline

- **Initial response**: Within 72 hours
- **Status update**: Weekly until resolved
- **Resolution target**: 90 days maximum
- **Public disclosure**: After fix is released

### Security Best Practices

#### For Users

1. **Change default tokens**
   ```bash
   # NEVER use the default service token in production
   SERVICE_TOKEN=your_secure_random_token_here
   ```

2. **Use HTTPS in production**
   ```bash
   # Configure secure endpoints
   TELEGRAM_WEBHOOK_URL=https://yourdomain.com/webhook
   ```

3. **Secure database connections**
   ```bash
   # Use SSL for database connections
   DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
   ```

4. **Keep dependencies updated**
   ```bash
   rye sync --update-all
   ```

#### For Developers

1. **Input validation**
   ```python
   # Always validate external inputs
   from pydantic import BaseModel, validator
   
   class UserInput(BaseModel):
       text: str
       
       @validator('text')
       def validate_text(cls, v):
           if len(v) > 1000:
               raise ValueError('Text too long')
           return v
   ```

2. **Service authentication**
   ```python
   # Use service tokens for inter-service communication
   from src.rssbot.core.security import verify_service_token
   
   @router.post("/endpoint")
   async def endpoint(token: str = Depends(verify_service_token)):
       # Secured endpoint
   ```

3. **Environment variables**
   ```python
   # Never hardcode secrets
   api_key = os.getenv("API_KEY")  # ✅ Good
   api_key = "sk-123456789"        # ❌ Bad
   ```

### Security Features

#### Built-in Protection

1. **Service Token Authentication**
   - All inter-service communication requires valid tokens
   - Configurable token validation
   - Automatic token rotation support

2. **Input Sanitization**
   - Pydantic models for request validation
   - SQL injection prevention via SQLModel
   - XSS protection in HTML responses

3. **Rate Limiting**
   - Configurable rate limits per endpoint
   - Built-in DoS protection
   - Telegram API rate limit compliance

4. **Secure Defaults**
   - HTTPS-only in production mode
   - Secure cookie settings
   - CORS properly configured

#### Configuration Security

1. **Environment Variables**
   ```bash
   # Required security settings
   SERVICE_TOKEN=generate_secure_random_token
   TELEGRAM_BOT_TOKEN=your_bot_token
   DATABASE_URL=your_database_url
   
   # Optional but recommended
   REDIS_URL=redis://localhost:6379/0
   ENVIRONMENT=production
   LOG_LEVEL=INFO
   ```

2. **Production Checklist**
   - [ ] Change default service token
   - [ ] Enable HTTPS for all endpoints
   - [ ] Configure firewall rules
   - [ ] Set up monitoring and logging
   - [ ] Regular security updates
   - [ ] Database connection encryption
   - [ ] Backup and recovery procedures

### Common Vulnerabilities

#### Prevented by Design

1. **SQL Injection**: SQLModel with parameterized queries
2. **XSS**: Automatic HTML escaping in templates
3. **CSRF**: Service token authentication
4. **Path Traversal**: Restricted file access patterns
5. **Information Disclosure**: Structured error responses

#### Areas Requiring Attention

1. **File Uploads**: Validate file types and sizes
2. **External APIs**: Rate limiting and input validation
3. **User Content**: Sanitization of RSS feed content
4. **Webhook Security**: Verify Telegram webhook signatures

### Security Testing

#### Automated Scanning

```bash
# Run security checks
rye run bandit -r src/
rye run safety check
rye run semgrep --config=auto src/
```

#### Manual Testing

1. **Authentication bypass testing**
2. **Input validation testing**
3. **API endpoint security review**
4. **Configuration security audit**

### Security Updates

#### Notification Channels

- **GitHub Security Advisories**: Automatic notifications
- **Release Notes**: Security fixes highlighted
- **Email Alerts**: For critical vulnerabilities

#### Update Process

1. **Assess impact** of security updates
2. **Test in staging** environment
3. **Schedule maintenance** window
4. **Apply updates** and verify
5. **Monitor** for issues post-update

### Compliance

#### Standards

- **OWASP Top 10**: Regular assessment and mitigation
- **CWE**: Common Weakness Enumeration awareness
- **GDPR**: Privacy by design principles
- **SOC 2**: Security control framework compliance

#### Data Protection

1. **Data Minimization**: Collect only necessary data
2. **Encryption**: At rest and in transit
3. **Access Control**: Role-based permissions
4. **Audit Logging**: Security event tracking
5. **Data Retention**: Automatic cleanup policies

### Contact Information

- **Security Team**: security@rssbot.com
- **General Contact**: contact@rssbot.com
- **GitHub**: @rssbot/security-team

### Acknowledgments

We appreciate the security research community and will acknowledge responsible disclosure contributors in our security advisories and release notes.

---

**Last Updated**: 2024-01-01  
**Next Review**: 2024-04-01