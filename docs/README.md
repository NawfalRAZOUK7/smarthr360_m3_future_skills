# SmartHR360 - M3 Future Skills Documentation

Complete documentation for the SmartHR360 Future Skills AI system.

## 📚 Contents

### Getting Started

- [Quick Commands](development/quick_commands.md) - Essential commands for development
- [Testing Guide](development/testing.md) - How to run and write tests
- [Monitoring & Logs](development/monitoring_logs_guide.md) - System monitoring and logging

### API Documentation

- [Permissions](api/permissions.md) - User roles and permissions documentation
- API Endpoints _(coming soon)_

### Machine Learning

- [ML Overview](../ml/docs/README.md) - Machine learning system overview
- [Architecture](../ml/docs/architecture.md) - ML system architecture
- [MLOps Guide](../ml/docs/mlops_guide.md) - ML operations and deployment
- [Model Comparison](../ml/docs/model_comparison.md) - Model evaluation results
- [Model Registry](../ml/docs/model_registry.md) - Model version management
- [Explainability](../ml/docs/explainability.md) - AI explainability and interpretability
- [Quick Reference](../ml/docs/quick_reference.md) - ML quick reference guide
- [Experiments Guide](../ml/docs/quick_reference_experiments.md) - Running experiments

### ML Documentation Archive

- [ML vs Rules Comparison](ml/ML_VS_RULES_COMPARISON.md)
- [ML Documentation](ml/ML_DOCUMENTATION_TO_ADD.md)
- [ML3 Summary](ml/ML3_SUMMARY.md)

### Deployment

- Docker Setup _(coming soon)_
- Production Guide _(coming soon)_

### Guides & Reference Sheets

- [Setup Guide](guides/SETUP_GUIDE.md) - Full environment setup walkthrough
- [Quickstart](guides/QUICKSTART.md) - Rapid onboarding checklist
- [Configuration Cheatsheet](guides/CONFIG_CHEATSHEET.md) - Frequently used config toggles
- [Resource Sizing Guide](guides/RESOURCE_SIZING_GUIDE.md) - Capacity planning reference
- [Project Structure](guides/PROJECT_STRUCTURE.md) - Source tree overview
- [Deployment Example](guides/DEPLOYMENT_EXAMPLE.md) - Sample end-to-end deployment
- [Kubernetes Deployment](guides/KUBERNETES_DEPLOYMENT.md) - Cluster rollout steps
- [CI/CD Quick Reference](guides/CI_CD_QUICK_REFERENCE.md) - Pipeline commands at a glance
- [ML Test Commands](guides/ML_TEST_COMMANDS.md) - Frequently used pytest targets
- [Workflow Diagram](guides/WORKFLOW_DIAGRAM.md) - Visual system flow

### Reports & Summaries

- [API Architecture Completion](reports/API_ARCHITECTURE_COMPLETION.md) - Status of API deliverables
- [CI/CD Implementation Summary](reports/CI_CD_IMPLEMENTATION_SUMMARY.md) - Pipeline hardening recap
- [Configuration Implementation Summary](reports/CONFIGURATION_IMPLEMENTATION_SUMMARY.md) - Environment config updates
- [Database Optimization Summary](reports/DATABASE_OPTIMIZATION_SUMMARY.md) - DB tuning outcomes
- [Documentation Summary](reports/DOCUMENTATION_SUMMARY.md) - Docs coverage review
- [Project Cleanup Summary](reports/PROJECT_CLEANUP_SUMMARY.md) - Technical debt removal log
- [Testing Strategy Completion](reports/TESTING_STRATEGY_COMPLETION_SUMMARY.md) - QA strategy milestone
- [Prediction Engine Test Coverage](reports/PREDICTION_ENGINE_TEST_COVERAGE_SUMMARY.md) - Model validation metrics
- [Training Service Test Coverage](reports/TRAINING_SERVICE_TEST_COVERAGE_SUMMARY.md) - Training API validation metrics
- [CI Test Failures Fixed](reports/CI_TEST_FAILURES_FIXED.md) - Catalog of resolved CI failures
- [Coverage Thresholds](reports/COVERAGE_THRESHOLDS.md) - Target coverage matrix

### Project Milestones

#### Learning Track (LT)

- [LT1 Completion Summary](milestones/LT1_COMPLETION_SUMMARY.md)
- [LT1 Explainability Guide](milestones/LT1_EXPLAINABILITY_GUIDE.md)
- [LT1 Quick Commands](milestones/LT1_QUICK_COMMANDS.md)
- [LT2 Completion Summary](milestones/LT2_COMPLETION_SUMMARY.md)
- [LT3 Completion Summary](milestones/LT3_COMPLETION_SUMMARY.md)

#### Main Track (MT)

- [MT1 Completion](milestones/MT1_COMPLETION.md)
- [MT1 Dataset Enrichment](milestones/MT1_DATASET_ENRICHMENT.md)
- [MT1 Summary](milestones/MT1_SUMMARY.md)
- [MT2 Monitoring Completion](milestones/MT2_MONITORING_COMPLETION.md)
- [MT3 Completion](milestones/MT3_COMPLETION.md)
- [MT3 Index](milestones/MT3_INDEX.md)
- [MT3 Summary](milestones/MT3_SUMMARY.md)
- [MT3 Visual Overview](milestones/MT3_VISUAL_OVERVIEW.md)
- [Step 9.4 Recap](milestones/step_9.4_recap.md)

### Project Overview

- [Complete Overview](overview.md) - Comprehensive project documentation summary

### Runbooks

- [Environment Asset Matrix](runbooks/ENVIRONMENTS.md) - Maps Dockerfiles, Makefiles, and requirements sets to their target environments

## 🔗 Quick Links

- [Main README](../README.md) - Project quick start
- [Makefile](../Makefile) - Build and development commands
- [ML Directory](../ml/) - Machine learning code and models
- [Future Skills App](../future_skills/) - Django application code

## 📝 Documentation Structure

```
docs/
├── README.md (this file)
├── overview.md
├── api/
│   └── permissions.md
├── development/
│   ├── quick_commands.md
│   ├── testing.md
│   └── monitoring_logs_guide.md
├── ml/
│   ├── ML_VS_RULES_COMPARISON.md
│   ├── ML_DOCUMENTATION_TO_ADD.md
│   └── ML3_SUMMARY.md
├── milestones/
│   ├── LT1_*.md
│   ├── LT2_*.md
│   ├── LT3_*.md
│   ├── MT1_*.md
│   ├── MT2_*.md
│   └── MT3_*.md
├── deployment/ (planned)
├── runbooks/
│   └── ENVIRONMENTS.md
├── guides/
│   ├── QUICKSTART.md
│   └── SETUP_GUIDE.md
├── reports/
│   ├── DOCUMENTATION_SUMMARY.md
│   └── PROJECT_CLEANUP_SUMMARY.md
└── assets/
    └── screenshots/
```

## 🎯 Getting Help

- For development setup, see [Quick Commands](development/quick_commands.md)
- For API usage, see [Permissions](api/permissions.md)
- For ML operations, see [ML Documentation](../ml/docs/README.md)
- For project history, browse [Milestones](milestones/)
