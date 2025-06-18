# NovaPort-MCP Update Guide

## Overview

This guide provides comprehensive procedures for updating NovaPort-MCP across different versions. Each major and minor version update includes specific migration steps, configuration changes, and compatibility considerations to ensure smooth transitions.

## Version Numbering Standards

NovaPort-MCP follows [Semantic Versioning](https://semver.org/) (SemVer):

- **MAJOR.MINOR.PATCH** (e.g., `1.2.3`)
- **MAJOR**: Breaking changes requiring migration
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

### Pre-release Versions
- **Alpha** (`1.0.0-alpha.1`): Early development, unstable
- **Beta** (`1.0.0-beta.1`): Feature complete, testing phase
- **Release Candidate** (`1.0.0-rc.1`): Production candidate

## General Update Procedures

### Before Any Update

1. **Create Backup**: Always backup your workspace data before updates
2. **Review Release Notes**: Read the specific version's release notes
3. **Test Environment**: Update a test environment first
4. **Check Dependencies**: Ensure Python and Poetry versions meet requirements

### Standard Update Process

```bash
# 1. Navigate to your NovaPort-MCP directory
cd /path/to/novaport-mcp

# 2. Create backup (recommended)
cp -r .novaport_data .novaport_data.backup.$(date +%Y%m%d)

# 3. Pull latest changes
git fetch origin
git checkout v[VERSION]  # Replace with target version

# 4. Update dependencies
poetry install

# 5. Verify installation
poetry run conport --version
```

## Version Migration Templates

### Template: Major Version Migration (X.0.0)

**Example: v1.0.0 → v2.0.0**

#### Breaking Changes Assessment
- [ ] **API Changes**: Review endpoint modifications
- [ ] **Schema Changes**: Check database schema breaking changes
- [ ] **Configuration Changes**: Update environment variables
- [ ] **Dependency Changes**: Verify compatibility with new dependencies

#### Pre-Migration Steps
1. **Complete Backup**:
   ```bash
   # Backup entire workspace data directory
   tar -czf novaport-backup-$(date +%Y%m%d).tar.gz .novaport_data/
   ```

2. **Version Compatibility Check**:
   ```bash
   # Check current version
   poetry run conport --version
   
   # Verify Python compatibility
   python --version
   ```

#### Migration Procedure
1. **Update Source Code**:
   ```bash
   git checkout v2.0.0
   poetry install
   ```

2. **Run Migration Scripts** (if provided):
   ```bash
   poetry run python -m conport.migrations.v2_0_0
   ```

3. **Update Configuration**:
   - Review `.env.example` for new variables
   - Update workspace settings in VS Code
   - Modify MCP server configuration if required

#### Post-Migration Verification
- [ ] **Database Integrity**: Verify all workspaces load correctly
- [ ] **API Functionality**: Test critical endpoints
- [ ] **Search Capabilities**: Verify vector search still functions
- [ ] **Integration Tests**: Run full test suite

#### Rollback Procedure
If migration fails:
```bash
# 1. Stop the server
# 2. Restore from backup
rm -rf .novaport_data/
tar -xzf novaport-backup-YYYYMMDD.tar.gz

# 3. Revert to previous version
git checkout v1.x.x
poetry install
```

### Template: Minor Version Update (X.Y.0)

**Example: v1.1.0 → v1.2.0**

#### New Features Assessment
- [ ] **New API Endpoints**: Review added functionality
- [ ] **Enhanced Features**: Check improved existing features
- [ ] **New Dependencies**: Verify new package requirements
- [ ] **Configuration Options**: Review new settings

#### Update Procedure
1. **Standard Update**:
   ```bash
   git checkout v1.2.0
   poetry install
   ```

2. **Configuration Review**:
   - Check for new optional environment variables
   - Review updated `.env.example`

3. **Feature Verification**:
   - Test new features if planning to use them
   - Verify existing functionality remains intact

#### Post-Update Checklist
- [ ] **All Workspaces Load**: Verify existing projects still work
- [ ] **New Features**: Test any new features you plan to use
- [ ] **Performance**: Check for any performance improvements

### Template: Patch Version Update (X.Y.Z)

**Example: v1.1.1 → v1.1.2**

#### Bug Fix Assessment
- [ ] **Fixed Issues**: Review resolved bugs
- [ ] **Security Patches**: Check for security improvements
- [ ] **Performance Fixes**: Note any performance enhancements

#### Quick Update Procedure
```bash
# Simple update for patch versions
git checkout v1.1.2
poetry install

# Restart server
poetry run conport
```

## Database Migration Handling

### Automatic Migrations

NovaPort-MCP uses Alembic for automatic database migrations:

1. **Per-Workspace Migration**: Each workspace database is migrated individually
2. **Automatic Execution**: Migrations run automatically on first access after update
3. **Migration Logging**: Check logs for migration status

### Manual Migration (if required)

For major versions that require manual intervention:

```bash
# 1. Stop all servers using the workspace
# 2. Create database backup
cp .novaport_data/conport.db .novaport_data/conport.db.backup

# 3. Run manual migration (if provided)
poetry run alembic upgrade head

# 4. Verify migration success
poetry run python -c "from conport.db.database import verify_schema; verify_schema()"
```

### Migration Troubleshooting

**Common Issues**:
- **Migration Conflict**: Manual schema changes conflict with migrations
- **Corrupted Database**: Database file corruption during migration
- **Version Skipping**: Attempting to skip versions

**Resolution Steps**:
1. **Restore from Backup**: Always first option
2. **Clean Migration**: Drop and recreate database (loses data)
3. **Contact Support**: For complex migration issues

## Configuration Changes

### Environment Variables

Each version may introduce new environment variables:

#### v0.1.0-beta Configuration
```bash
# Core Settings
PROJECT_NAME="NovaPort MCP"
EMBEDDING_MODEL_NAME="all-MiniLM-L6-v2"
DATABASE_URL="sqlite:///./dummy_for_alembic_cli.db"  # CLI only
```

#### Template: New Version Configuration
```bash
# Previous variables (maintain)
PROJECT_NAME="NovaPort MCP"
EMBEDDING_MODEL_NAME="all-MiniLM-L6-v2"

# New in vX.Y.Z (add these)
NEW_FEATURE_ENABLED=true
PERFORMANCE_CACHE_SIZE=1000
```

### VS Code Integration Updates

When MCP server configuration changes:

1. **Update settings.json**:
   ```json
   {
     "mcpServers": {
       "novaport-mcp": {
         "command": "poetry",
         "args": ["run", "conport"],
         "cwd": "/path/to/novaport-mcp",
         "disabled": false,
         "description": "NovaPort MCP Server"
       }
     }
   }
   ```

2. **Restart VS Code**: After configuration changes

## Dependency Updates

### Python Version Requirements

- **v0.1.0-beta**: Python 3.11+
- **Future versions**: Check release notes for requirements

### Poetry Dependency Management

```bash
# Update all dependencies to latest compatible versions
poetry update

# Update specific dependency
poetry update sqlalchemy

# Check for outdated dependencies
poetry show --outdated
```

### Dependency Conflicts

If dependency conflicts arise:

1. **Clear Cache**:
   ```bash
   poetry cache clear pypi --all
   rm poetry.lock
   poetry install
   ```

2. **Manual Resolution**: Edit `pyproject.toml` if needed

## Backup Recommendations

### Automated Backup Strategy

1. **Pre-Update Backup**: Always before updates
2. **Regular Backups**: Weekly or before major changes
3. **Versioned Backups**: Keep multiple backup versions

### Backup Script Template

```bash
#!/bin/bash
# backup-workspace.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups"
WORKSPACE_DATA=".novaport_data"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create compressed backup
tar -czf "$BACKUP_DIR/novaport-backup-$DATE.tar.gz" "$WORKSPACE_DATA"

# Keep only last 10 backups
ls -t "$BACKUP_DIR"/novaport-backup-*.tar.gz | tail -n +11 | xargs rm -f

echo "Backup created: $BACKUP_DIR/novaport-backup-$DATE.tar.gz"
```

### Backup Verification

```bash
# Test backup integrity
tar -tzf backup-file.tar.gz > /dev/null && echo "Backup OK" || echo "Backup corrupted"

# Test restore process (in test environment)
tar -xzf backup-file.tar.gz -C test-restore/
```

## Troubleshooting Common Update Issues

### Server Won't Start After Update

1. **Check Python Version**: Ensure meets requirements
2. **Verify Dependencies**: Run `poetry install`
3. **Check Configuration**: Review `.env` file
4. **Clear Cache**: Remove any cached files

```bash
# Troubleshooting steps
poetry env info  # Check Python version
poetry install   # Reinstall dependencies
poetry run python -c "import conport; print('Import OK')"
```

### Database Migration Failures

1. **Check Migration Logs**: Look for specific error messages
2. **Verify Database Permissions**: Ensure write access
3. **Manual Migration**: Use Alembic commands directly
4. **Restore from Backup**: Last resort

### VS Code Integration Issues

1. **Restart VS Code**: Often resolves connection issues
2. **Check Server Path**: Verify `cwd` in settings.json
3. **Test Server Manually**: Run `poetry run conport` directly
4. **Check Output Panel**: Review MCP server logs in VS Code

### Performance Issues After Update

1. **Clear Vector Database**: Rebuild if search is slow
2. **Check Resource Usage**: Monitor memory/CPU usage
3. **Review New Settings**: Adjust new performance parameters
4. **Database Optimization**: Run VACUUM on SQLite databases

## Version-Specific Migration Guides

### v0.1.0-beta (Initial Release)

This is the initial beta release. No migration required from previous versions as this is a complete rewrite.

**Fresh Installation Only**: No upgrade path from original context-portal.

### Template: v0.2.0 (Future Release)

*This section will be populated when v0.2.0 is released*

#### Expected Changes
- TBD: PostgreSQL optimizations
- TBD: Enhanced search capabilities
- TBD: Performance improvements

#### Migration Steps
- TBD: Specific migration procedures
- TBD: Configuration changes required
- TBD: New features to configure

## Support and Resources

### Documentation
- **Release Notes**: [`RELEASE_NOTES.md`](./RELEASE_NOTES.md)
- **README**: [`README.md`](./README.md)
- **Technical Deep Dive**: [`docs/deep_dive.md`](./docs/deep_dive.md)

### Getting Help
- **GitHub Issues**: Report problems or ask questions
- **Documentation**: Check existing documentation first
- **Community**: Share experiences with other users

### Emergency Contacts
- **Critical Issues**: Create GitHub issue with "urgent" label
- **Security Issues**: Follow responsible disclosure in README

---

**Note**: This guide is updated with each release. Always refer to the version-specific sections for your particular update scenario.