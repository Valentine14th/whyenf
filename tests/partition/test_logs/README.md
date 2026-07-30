# Enforcement Test Suite

This directory contains test logs for the MiniTwitter GDPR enforcement system. Each log file tests specific GDPR compliance scenarios with actual predicates from the signature file.

The test cases are modelled against the actions implemented into the GDPRSocial application, such that enforcement results are comparable.

## Test Files

### Basic GDPR Rights (Art. 15-21)

1. **01_access_request.log** - Basic data access request (Art. 15)
   - User consents, creates data, then requests access
   - Tests: RequestAccess event

2. **02_portability_request.log** - Data portability without new controller (Art. 20)
   - User requests data in portable format
   - Tests: RequestAccess + IsPortabilityRequest

3. **03_portability_new_controller.log** - Data portability with new controller (Art. 20)
   - User requests data transfer to new controller
   - Tests: RequestAccess + IsPortabilityRequest + SpecifiesNewController

4. **04_rectification_request.log** - Data rectification request (Art. 16)
   - User requests correction of personal data
   - Tests: RequestRectification event

5. **05_objection_to_processing.log** - Objection to processing (Art. 21)
   - User objects to personalized advertising
   - Tests: RequestObjection event

6. **06_restriction_request.log** - Restriction of processing (Art. 18)
   - User requests restriction on specific purpose
   - Tests: IsRestrictionRequest event

7. **09_erasure_request.log** - Right to erasure (Art. 17)
   - User requests deletion of personal data
   - Tests: RequestErasure event

### Consent Management (Art. 6-7)

8. **07_consent_withdrawal.log** - Consent withdrawal
   - User gives consent, processes data, then revokes consent
   - Tests: Consent + Revoke + processing suppression

9. **08_multi_purpose_consent.log** - Multiple purpose consent management
   - User manages consent for service, ads, and statistics independently
   - Tests: Multiple Consent/Revoke for different purposes

10. **10_special_category_consent.log** - Special category data consent (Art. 9)
    - Explicit consent for health data processing
    - Tests: SpecialConsent + IsSpecialData

11. **11_consent_before_processing.log** - Processing without consent
    - Data collected before consent given
    - Tests: Enforcement should prevent/suppress processing

### Complex Scenarios

12. **12_multi_user_scenario.log** - Multi-user interactions
    - Multiple users with data interactions
    - Tests: Cross-user data access patterns

13. **13_restriction_then_lift.log** - Restriction lifecycle
    - Request restriction, enforce it, then lift it
    - Tests: IsRestrictionRequest + LiftRestriction

14. **14_data_collection_tracking.log** - Collection tracking
    - Multiple Collect events for different activities
    - Tests: Collect event tracking across activities

15. **15_sequential_requests.log** - Multiple request types
    - User makes access, rectification, and erasure requests in sequence
    - Tests: Multiple request types for same user

16. **16_complex_multi_user_scenario.log** - Comprehensive multi-user test (904 lines)
    - 5 users performing interleaved GDPR operations
    - Covers all request types, consent management, special category data
    - Includes data sharing, restrictions, and recipient notifications
    - Tests: Complex real-world scenarios with concurrent operations

## Running Tests

Use the EnfGuard monitoring tool with these logs:

```bash
./enfguard.exe -formula policy.mfotl -sig minitwit_gdpr.sig -log test.log
```

## Log Format

Each log follows the standard EnfGuard format:
- `@timestamp event(args...);` - Input events at specific timestamps
- `@timestamp tick();` - Time progression
- Multiple events at same timestamp are space-separated on same line

No comments are included in log files (not accepted by runner).
