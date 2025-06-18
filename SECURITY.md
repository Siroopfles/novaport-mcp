# Security Policy

## Overview

The NovaPort-MCP project takes security seriously. As a Model Context Protocol server that handles structured project context and potentially sensitive development information, we are committed to ensuring the security and privacy of our users' data.

This document outlines our security policy, including how to report vulnerabilities, our response process, and security best practices for users.

## Supported Versions

We actively maintain security updates for the following versions of NovaPort-MCP:

| Version | Supported          | Status |
| ------- | ------------------ | ------ |
| 0.1.x   | ✅ Yes             | Current Beta |
| < 0.1.0 | ❌ No              | Pre-release |

**Note**: As we are currently in beta (0.1.0-beta), we recommend users stay up-to-date with the latest version to receive all security patches.

## Reporting Security Vulnerabilities

### How to Report

**DO NOT** report security vulnerabilities through public GitHub issues, discussions, or pull requests.

Instead, please report security vulnerabilities responsibly by:

**Email**: selfpooris@gmail.com  
**Subject**: [SECURITY] Brief description of the vulnerability

### What to Include

When reporting a security vulnerability, please include:

1. **Description**: A clear description of the vulnerability
2. **Impact**: The potential impact and severity of the issue
3. **Reproduction Steps**: Detailed steps to reproduce the vulnerability
4. **Environment**: 
   - NovaPort-MCP version
   - Operating system and version
   - Python version
   - Database type (SQLite/PostgreSQL)
   - Any relevant configuration details
5. **Proof of Concept**: If possible, include a minimal proof of concept
6. **Suggested Fix**: If you have ideas for how to address the issue
7. **Credit Preference**: How you would like to be credited in the security advisory

### Example Report Template

```
Subject: [SECURITY] SQL Injection in Custom Data API

Description:
The custom data API endpoint appears to be vulnerable to SQL injection 
when processing certain special characters in the 'key' parameter.

Impact:
An attacker could potentially read, modify, or delete database contents
by crafting malicious requests to /custom-data endpoints.

Reproduction Steps:
1. Send POST request to /custom-data with payload: {...}
2. Observe that the SQL query is executed without proper sanitization
3. Database contents can be accessed through crafted SQL injection

Environment:
- NovaPort-MCP version: 0.1.0-beta
- OS: Ubuntu 22.04
- Python: 3.11.5
- Database: PostgreSQL 15

Proof of Concept:
[Include minimal example that demonstrates the issue]

Suggested Fix:
Use parameterized queries or improve input validation for the 'key' field.

Credit:
Please credit me as "Security Researcher John Doe"
```

## Response Timeline

We are committed to responding to security reports promptly:

| Timeline | Action |
|----------|--------|
| **24 hours** | Initial acknowledgment of report |
| **72 hours** | Initial assessment and severity classification |
| **7 days** | Detailed response with timeline for fix |
| **30 days** | Target resolution for high/critical issues |
| **90 days** | Target resolution for medium/low issues |

### Severity Classification

We use the following severity levels:

- **Critical**: Immediate threat to user data or system integrity
- **High**: Significant security risk with practical exploit potential
- **Medium**: Security risk with limited impact or difficult exploitation
- **Low**: Minor security improvements or theoretical risks

## Coordinated Disclosure Process

We follow responsible disclosure practices:

1. **Report Received**: We acknowledge your report within 24 hours
2. **Investigation**: We investigate and validate the vulnerability
3. **Fix Development**: We develop and test a security patch
4. **Coordination**: We coordinate release timing with the reporter
5. **Release**: We release the security update
6. **Disclosure**: We publish a security advisory crediting the reporter
7. **Follow-up**: We monitor for any additional issues or bypass attempts

### Disclosure Timeline

- **0-90 days**: Private coordination between reporter and maintainers
- **90+ days**: If no fix is available, we may discuss extended timeline
- **After fix**: Public disclosure through GitHub Security Advisory

## Security Best Practices for Users

### General Security

1. **Keep Updated**: Always use the latest version of NovaPort-MCP
2. **Monitor Advisories**: Subscribe to security notifications
3. **Secure Configuration**: Follow security configuration guidelines
4. **Access Control**: Implement proper access controls for your MCP server

### Database Security

1. **Database Access**: Secure your database with strong authentication
2. **Network Security**: Restrict database network access
3. **Encryption**: Use TLS/SSL for database connections in production
4. **Backup Security**: Secure your database backups

### Deployment Security

1. **Environment Variables**: Secure sensitive configuration
2. **Network Configuration**: Use firewalls and network segmentation
3. **Container Security**: If using Docker, follow container security best practices
4. **Log Security**: Secure and monitor application logs

### Configuration Security

```yaml
# Example secure configuration
database:
  # Use environment variables for sensitive data
  url: ${DATABASE_URL}
  
security:
  # Enable authentication in production
  require_auth: true
  
logging:
  # Avoid logging sensitive information
  level: "INFO"
  sanitize_logs: true
```

## Security Features

NovaPort-MCP includes several security features:

### Built-in Security

- **Input Validation**: Comprehensive input validation using Pydantic
- **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries
- **Error Handling**: Secure error handling that doesn't leak sensitive information
- **Logging**: Configurable logging with sensitive data filtering

### Authentication & Authorization

- **MCP Protocol Security**: Follows MCP security best practices
- **Database Security**: Secure database connection handling
- **API Security**: FastAPI security features and middleware

### Data Protection

- **Data Validation**: Strict data validation and sanitization
- **Privacy Controls**: User data privacy and retention controls
- **Audit Logging**: Optional audit logging for security monitoring

## Security Testing

We encourage security testing of NovaPort-MCP:

### Automated Testing

- **Static Analysis**: Regular static analysis with security linters
- **Dependency Scanning**: Automated dependency vulnerability scanning
- **Unit Tests**: Security-focused unit tests for critical components

### Manual Testing

- **Code Reviews**: Security-focused code reviews for all changes
- **Penetration Testing**: Regular security assessments
- **Vulnerability Research**: We welcome responsible security research

## Bug Bounty Program

Currently, NovaPort-MCP does not have a formal bug bounty program. However, we deeply appreciate security researchers who help improve our security:

- **Recognition**: Public recognition in security advisories
- **Hall of Fame**: Contributor recognition in project documentation
- **Direct Communication**: Direct access to maintainers for coordination

We are considering implementing a formal bug bounty program as the project grows.

## Security Contact

For all security-related matters:

**Primary Contact**: selfpooris@gmail.com  
**Response Time**: Within 24 hours  
**PGP Key**: Available upon request  

### Non-Security Issues

For non-security bugs and general issues, please use:
- **GitHub Issues**: https://github.com/siroopfles/novaport-mcp/issues
- **General Contact**: selfpooris@gmail.com

## Acknowledgments

We would like to thank the security researchers and community members who have helped improve NovaPort-MCP's security:

- Future contributors will be listed here

## Legal

### Safe Harbor

We support safe harbor for security researchers who:

- Make a good faith effort to avoid privacy violations and disruptions
- Only interact with accounts they own or with explicit permission
- Do not access or modify others' data
- Report vulnerabilities promptly and responsibly
- Do not violate any applicable laws or regulations

### Responsible Disclosure

By participating in our security process, you agree to:

- Allow reasonable time for investigation and remediation
- Avoid disclosing the issue publicly until coordination is complete
- Not exploit the vulnerability beyond what is necessary for proof of concept
- Not access, modify, or delete others' data

## Updates to This Policy

This security policy may be updated periodically. Significant changes will be:

- Announced through project communication channels
- Reflected in the version history below
- Effective immediately upon publication

### Version History

- **v1.0** (2025-06-18): Initial security policy

---

**Last Updated**: 2025-06-18  
**Policy Version**: 1.0  
**Next Review**: 2025-12-18