# Contributing to Gmail Automation Suite

Thank you for your interest in contributing to the Gmail Automation Suite! This document provides guidelines for contributing to this project.

## 🤝 How to Contribute

### Reporting Issues
- Use the GitHub issue tracker to report bugs
- Include detailed steps to reproduce the issue
- Provide your Python version and OS information
- Include relevant error messages and logs

### Suggesting Features
- Open an issue with the "enhancement" label
- Describe the feature and its use case
- Explain how it would benefit users

### Code Contributions

1. **Fork the Repository**
   ```bash
   git fork https://github.com/yourusername/gmail-automation-suite
   ```

2. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make Your Changes**
   - Follow the existing code style
   - Add comments for complex logic
   - Include error handling
   - Test your changes thoroughly

4. **Commit Your Changes**
   ```bash
   git commit -m "Add feature: your feature description"
   ```

5. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

## 📋 Development Guidelines

### Code Style
- Follow PEP 8 Python style guide
- Use meaningful variable and function names
- Include docstrings for all functions and classes
- Keep functions focused and single-purpose

### Testing
- Test all new features with real Gmail accounts (use test accounts)
- Verify error handling works correctly
- Test with different Gmail configurations
- Include rate limiting considerations

### Security
- Never commit credentials or tokens
- Use environment variables for sensitive data
- Follow OAuth 2.0 best practices
- Validate all user inputs

## 🔧 Development Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/gmail-automation-suite
   cd gmail-automation-suite
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Credentials**
   - Follow the README setup instructions
   - Use a test Gmail account for development

## 📝 Pull Request Guidelines

- **Clear Description**: Explain what your PR does and why
- **Small Changes**: Keep PRs focused on a single feature or fix
- **Update Documentation**: Update README.md if needed
- **Test Instructions**: Provide clear testing instructions
- **Breaking Changes**: Clearly mark any breaking changes

## 🏷️ Adding New Labels or Filters

When adding new label categories or filters:

1. **Research Common Patterns**: Look for widely-used email patterns
2. **Test Thoroughly**: Verify filters work with real emails
3. **Document Changes**: Update README with new categories
4. **Consider Internationalization**: Test with non-English senders
5. **Add Color Coding**: Choose appropriate colors for new labels

## 🐛 Bug Reports

Include the following in bug reports:

- **Python Version**: `python --version`
- **OS Information**: Operating system and version
- **Error Messages**: Full error traceback
- **Steps to Reproduce**: Detailed reproduction steps
- **Expected Behavior**: What should have happened
- **Actual Behavior**: What actually happened

## 💡 Feature Requests

For feature requests, please include:

- **Use Case**: Why this feature would be useful
- **Implementation Ideas**: Suggestions for how it could work
- **Examples**: Specific examples of the feature in action
- **Alternatives**: Any workarounds you've tried

## 📞 Getting Help

- Check existing issues and documentation first
- Create a new issue with the "question" label
- Be specific about what you're trying to achieve
- Include relevant code snippets

## 🙏 Recognition

Contributors will be recognized in the project README. Thank you for helping make Gmail automation better for everyone!

---

By contributing, you agree that your contributions will be licensed under the MIT License.