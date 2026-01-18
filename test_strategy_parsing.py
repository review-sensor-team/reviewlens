import os

# Simple Settings class for testing
class Settings:
    def __init__(self):
        self.PROMPT_STRATEGY = os.getenv('PROMPT_STRATEGY', 'default')
    
    def get_prompt_strategies(self):
        if not self.PROMPT_STRATEGY:
            return ['default']
        
        strategies = [s.strip() for s in self.PROMPT_STRATEGY.split(',') if s.strip()]
        return strategies if strategies else ['default']

# Test cases
test_cases = [
    ('default', ['default']),
    ('default,friendly', ['default', 'friendly']),
    ('default, friendly, concise', ['default', 'friendly', 'concise']),
    ('', ['default']),
    ('  default  ,  friendly  ', ['default', 'friendly']),
]

print('=' * 70)
print('Multi-Prompt Strategy Parsing Test')
print('=' * 70)
print()

all_passed = True
for input_str, expected in test_cases:
    os.environ['PROMPT_STRATEGY'] = input_str
    settings = Settings()
    result = settings.get_prompt_strategies()
    
    passed = result == expected
    all_passed = all_passed and passed
    status = 'PASS' if passed else 'FAIL'
    
    print(f'[{status}] Input: "{input_str}"')
    print(f'       Expected: {expected}')
    print(f'       Got:      {result}')
    print()

if all_passed:
    print('All tests passed!')
else:
    print('Some tests failed!')
