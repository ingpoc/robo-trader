# Full-Stack Development Workflow

## Overview
This document outlines the standardized workflow for handling full-stack development in the Robo Trader project, which uses a segregated architecture with React frontend and FastAPI backend. The workflow follows the **"plan-develop-integrate-test-deploy"** cycle to ensure seamless frontend-backend coordination and prevent integration issues.

## 🔄 Plan-Develop-Integrate-Test-Deploy Cycle

### Phase 1: Planning & Architecture
**When a user suggests a feature or bug fix:**

#### Step 1: Requirements Analysis
- [ ] Read and understand the user's request completely
- [ ] Identify frontend and backend components affected
- [ ] Determine API contract changes needed
- [ ] Check for related existing issues or patterns
- [ ] Assess impact on segregated architecture

#### Step 2: Architecture Design
- [ ] **MANDATORY**: Read `.kilocode/rules/ui-rules.md` completely
- [ ] Design API endpoints and data contracts
- [ ] Plan frontend state management changes
- [ ] Identify WebSocket integration needs
- [ ] Document cross-cutting concerns (auth, error handling)

#### Step 3: Implementation Planning
- [ ] Create detailed implementation plan for both stacks
- [ ] Identify files that need modification in frontend and backend
- [ ] Plan testing strategy for integration points
- [ ] Document assumptions and dependencies
- [ ] Coordinate with team for parallel development

### Phase 2: Backend Development
**Implement backend changes first (API-first approach):**

#### Step 1: API Design & Implementation
- [ ] Define OpenAPI specifications for new endpoints
- [ ] Implement FastAPI routes with proper validation
- [ ] Add CORS configuration if needed
- [ ] Implement WebSocket handlers if required
- [ ] Write comprehensive backend tests

#### Step 2: Business Logic
- [ ] Implement core business logic
- [ ] Add proper error handling and logging
- [ ] Implement security measures (auth, validation)
- [ ] Add monitoring and metrics

#### Step 3: Backend Testing
- [ ] Unit tests for all new functions
- [ ] Integration tests for API endpoints
- [ ] Load testing for performance-critical endpoints
- [ ] Security testing and validation

### Phase 3: Frontend Development
**Implement frontend changes after backend is ready:**

#### Step 1: API Integration
- [ ] Update TypeScript types for new API contracts
- [ ] Implement API client functions
- [ ] Add WebSocket integration if needed
- [ ] Implement error handling and retry logic

#### Step 2: Component Development
- [ ] Create/update React components following UI rules
- [ ] Implement state management (Zustand/TanStack Query)
- [ ] Add proper loading states and error boundaries
- [ ] Ensure accessibility compliance

#### Step 3: UI/UX Implementation
- [ ] Follow Swiss Digital Minimalism principles
- [ ] Implement responsive design (mobile-first)
- [ ] Add proper focus management and keyboard navigation
- [ ] Test on multiple screen sizes and devices

### Phase 4: Integration & Testing
**Ensure seamless frontend-backend integration:**

#### Step 1: Integration Testing
- [ ] Test API calls from frontend to backend
- [ ] Verify WebSocket connections and real-time updates
- [ ] Test error scenarios and edge cases
- [ ] Validate CORS and cross-origin requests

#### Step 2: End-to-End Testing
- [ ] Test complete user workflows
- [ ] Verify data flow between frontend and backend
- [ ] Test authentication and authorization
- [ ] Performance testing across the full stack

#### Step 3: Cross-Browser Testing
- [ ] Test on supported browsers (Chrome, Firefox, Safari, Edge)
- [ ] Verify responsive design on different screen sizes
- [ ] Test accessibility features with screen readers
- [ ] Validate performance metrics (< 2s load time)

### Phase 5: Deployment & Monitoring
**Deploy changes to production environment:**

#### Step 1: Pre-Deployment Checks
- [ ] Run full test suite (frontend + backend)
- [ ] Verify environment configurations
- [ ] Check CORS settings for production domains
- [ ] Validate API endpoint URLs and WebSocket connections
- [ ] Performance testing in staging environment

#### Step 2: Deployment Execution
- [ ] Deploy backend first (API-first deployment)
- [ ] Deploy frontend after backend is verified
- [ ] Update environment variables and configurations
- [ ] Run database migrations if needed
- [ ] Verify health checks pass

#### Step 3: Post-Deployment Validation
- [ ] Monitor error rates and performance metrics
- [ ] Verify WebSocket connections work in production
- [ ] Test critical user workflows
- [ ] Monitor for any integration issues

### Phase 6: Feedback & Iteration
**If issues are discovered post-deployment:**

#### Step 1: Issue Triage
- [ ] Analyze error logs and user reports
- [ ] Identify whether issue is frontend, backend, or integration-related
- [ ] Determine severity and impact
- [ ] Coordinate with team for rapid response

#### Step 2: Root Cause Analysis
- [ ] Review code changes against established patterns
- [ ] Check for integration points that may have failed
- [ ] Verify API contracts and data flow
- [ ] Identify gaps in testing or monitoring

#### Step 3: Hotfix Implementation
- [ ] Implement fixes following established workflow
- [ ] Prioritize critical issues for immediate deployment
- [ ] Ensure fixes don't break existing functionality
- [ ] Add additional monitoring for similar issues

#### Step 4: Retrospective & Improvement
- [ ] Document lessons learned from the issue
- [ ] Update workflows or rules if gaps were found
- [ ] Improve testing coverage for problematic areas
- [ ] Share findings with the development team

### Phase 3: Reflection & Rule Updates
**Once the user agrees that the fixes are satisfactory:**

#### Step 1: Process Reflection
- [ ] Document what went wrong in the initial implementation
- [ ] Identify gaps in current UI rules that allowed the mistake
- [ ] Analyze whether rules were unclear, incomplete, or misinterpreted
- [ ] Consider if new patterns or guidelines are needed

#### Step 2: Mistake Analysis
- [ ] Categorize the type of mistake:
  - Rule misinterpretation
  - Missing rule coverage
  - Implementation error
  - Requirements misunderstanding
- [ ] Document specific scenarios that weren't covered

#### Step 3: Rule Enhancement
- [ ] Update `.kilocode/rules/ui-rules.md` with:
  - New rules to prevent similar issues
  - Clarified existing rules
  - Additional examples or patterns
  - Enhanced checklists or guidelines
- [ ] Ensure updates are specific and actionable

#### Step 4: Documentation
- [ ] Update workflow documentation if needed
- [ ] Add examples from the resolved issue
- [ ] Document lessons learned for future reference

## 📋 Workflow Guidelines

### Communication Standards
- **Be specific** about what was changed in frontend and backend
- **Document API contracts** clearly for integration points
- **Ask clarifying questions** when requirements are unclear
- **Provide context** for architectural decisions
- **Coordinate** between frontend and backend developers

### Quality Gates
- **Never skip** the pre-commit checklist for both stacks
- **Always test** integration points thoroughly
- **Verify CORS** and cross-origin functionality
- **Check WebSocket** connections and real-time updates
- **Test end-to-end** user workflows
- **Monitor performance** across the full stack

### Architecture Adherence
- **API-first development** - Backend APIs defined before frontend
- **Maintain segregation** - No business logic in frontend
- **Follow established patterns** for both React and FastAPI
- **Update rules** when architectural gaps are discovered
- **Document integration points** clearly

## 🚨 Emergency Procedures

### When Architecture Conflicts with Requirements
1. Document the conflict clearly with technical justification
2. Propose architecture modification with impact analysis
3. Get approval from architecture team before proceeding
4. Update documentation and rules post-implementation
5. Plan migration path for existing integrations

### When Integration Blocks Progress
1. Identify specific integration issues (API, WebSocket, CORS)
2. Document technical constraints and error patterns
3. Implement temporary workarounds with monitoring
4. Create detailed issue tickets for permanent fixes
5. Update integration testing to prevent similar issues

### When Deployment Issues Occur
1. Roll back to previous working version immediately
2. Analyze deployment logs for root cause
3. Fix issues in staging environment first
4. Implement additional health checks and monitoring
5. Update deployment procedures to prevent recurrence

## 📊 Success Metrics

### Quality Indicators
- [ ] Zero integration regressions (API/WebSocket failures)
- [ ] All user workflows complete successfully
- [ ] CORS and cross-origin requests work properly
- [ ] Real-time updates via WebSocket function correctly
- [ ] Performance meets targets (< 2s load, 60fps animations)
- [ ] Accessibility standards maintained across stacks
- [ ] No console errors in production

### Process Indicators
- [ ] API contracts documented and followed
- [ ] Frontend and backend developed in parallel efficiently
- [ ] Integration testing completed before deployment
- [ ] Rules and workflows updated when gaps discovered
- [ ] Cross-team communication effective and documented
- [ ] Deployment process reliable and monitored

## 🔗 Related Documentation

- **UI Rules**: `.kilocode/rules/ui-rules.md` - Mandatory rules and patterns for segregated architecture
- **Backend Integration**: `BACKEND_FRONTEND_INTEGRATION.md` - CORS, API, and WebSocket setup
- **Project Summary**: `ui/PROJECT_SUMMARY.md` - React frontend implementation details
- **Design Principles**: `ui/DESIGN_PRINCIPLES.md` - Swiss Digital Minimalism guidelines
- **Quick Start**: `QUICK_START.md` - Development environment setup
- **Code Review**: UI rules include automatic rejection criteria for both stacks

## 🎯 Key Principles

1. **API-First Development**: Design and implement backend APIs before frontend integration
2. **Segregation Enforcement**: Maintain strict separation between frontend and backend concerns
3. **Integration Testing**: Test frontend-backend integration thoroughly at every stage
4. **Parallel Development**: Enable efficient parallel development of frontend and backend
5. **Deployment Coordination**: Deploy backend first, then frontend to minimize downtime
6. **Monitoring & Observability**: Implement comprehensive monitoring across both stacks
7. **Continuous Integration**: Automate testing and deployment for both frontend and backend
8. **Documentation Sync**: Keep API documentation synchronized between frontend and backend

This workflow ensures that full-stack development is coordinated, reliable, and scalable while maintaining the benefits of segregated architecture.