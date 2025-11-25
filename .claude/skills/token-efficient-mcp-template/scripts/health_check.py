#!/usr/bin/env python3
"""
Health Check Script for Token-Efficient MCP & Hook System
Validates system connectivity, configuration, and token efficiency metrics.
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import subprocess
import importlib.util

class HealthChecker:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.results = {
            'overall_status': 'unknown',
            'components': {},
            'token_efficiency': {},
            'recommendations': []
        }

    async def run_all_checks(self) -> Dict[str, Any]:
        """Run comprehensive health checks."""
        print("🔍 Running Token-Efficient System Health Checks...\n")

        # Check project structure
        await self._check_project_structure()

        # Check configuration files
        await self._check_configuration()

        # Check hook system
        await self._check_hook_system()

        # Check MCP server
        await self._check_mcp_server()

        # Check token efficiency setup
        await self._check_token_efficiency()

        # Calculate overall status
        self._calculate_overall_status()

        # Generate recommendations
        self._generate_recommendations()

        return self.results

    async def _check_project_structure(self):
        """Check if project structure is correct."""
        print("📁 Checking project structure...")

        required_dirs = [
            'hooks',
            'mcp_server',
            'config',
            'scripts',
            'docs'
        ]

        missing_dirs = []
        for dir_name in required_dirs:
            dir_path = self.project_dir / dir_name
            if dir_path.exists():
                self.results['components'][f'directory_{dir_name}'] = {
                    'status': 'healthy',
                    'message': f'{dir_name}/ directory exists'
                }
            else:
                missing_dirs.append(dir_name)
                self.results['components'][f'directory_{dir_name}'] = {
                    'status': 'error',
                    'message': f'Missing {dir_name}/ directory'
                }

        if missing_dirs:
            print(f"  ❌ Missing directories: {', '.join(missing_dirs)}")
        else:
            print("  ✅ All required directories present")

    async def _check_configuration(self):
        """Check configuration files."""
        print("⚙️ Checking configuration...")

        config_files = [
            'config/main.yaml',
            'config/cache_config.json'
        ]

        for config_file in config_files:
            file_path = self.project_dir / config_file
            if file_path.exists():
                try:
                    if config_file.endswith('.json'):
                        with open(file_path) as f:
                            json.load(f)
                    elif config_file.endswith('.yaml'):
                        import yaml
                        with open(file_path) as f:
                            yaml.safe_load(f)

                    self.results['components'][f'config_{config_file.split("/")[-1]}'] = {
                        'status': 'healthy',
                        'message': f'Configuration file {config_file} is valid'
                    }
                    print(f"  ✅ {config_file} - Valid")
                except Exception as e:
                    self.results['components'][f'config_{config_file.split("/")[-1]}'] = {
                        'status': 'error',
                        'message': f'Invalid configuration: {e}'
                    }
                    print(f"  ❌ {config_file} - Invalid: {e}")
            else:
                self.results['components'][f'config_{config_file.split("/")[-1]}'] = {
                    'status': 'warning',
                    'message': f'Configuration file {config_file} not found'
                }
                print(f"  ⚠️ {config_file} - Not found")

    async def _check_hook_system(self):
        """Check hook system setup."""
        print("🪝 Checking hook system...")

        hook_dirs = [
            'hooks/pre_tool_use',
            'hooks/context_injection',
            'hooks/session_management'
        ]

        for hook_dir in hook_dirs:
            dir_path = self.project_dir / hook_dir
            if dir_path.exists():
                # Check for hook scripts
                scripts = list(dir_path.glob('*.sh')) + list(dir_path.glob('*.py'))
                if scripts:
                    self.results['components'][f'hook_{hook_dir.split("/")[-1]}'] = {
                        'status': 'healthy',
                        'message': f'{len(scripts)} hook scripts found',
                        'scripts': [s.name for s in scripts]
                    }
                    print(f"  ✅ {hook_dir} - {len(scripts)} scripts")
                else:
                    self.results['components'][f'hook_{hook_dir.split("/")[-1]}'] = {
                        'status': 'warning',
                        'message': 'No hook scripts found'
                    }
                    print(f"  ⚠️ {hook_dir} - No scripts")
            else:
                self.results['components'][f'hook_{hook_dir.split("/")[-1]}'] = {
                    'status': 'error',
                    'message': 'Hook directory not found'
                }
                print(f"  ❌ {hook_dir} - Directory not found")

    async def _check_mcp_server(self):
        """Check MCP server setup."""
        print("🚀 Checking MCP server...")

        server_dir = self.project_dir / 'mcp_server'
        if not server_dir.exists():
            self.results['components']['mcp_server'] = {
                'status': 'error',
                'message': 'MCP server directory not found'
            }
            print("  ❌ MCP server directory not found")
            return

        # Check for main server file
        main_py = server_dir / 'server' / 'main.py'
        if main_py.exists():
            self.results['components']['mcp_server_main'] = {
                'status': 'healthy',
                'message': 'MCP server main file exists'
            }
            print("  ✅ MCP server main file found")
        else:
            self.results['components']['mcp_server_main'] = {
                'status': 'error',
                'message': 'MCP server main file missing'
            }
            print("  ❌ MCP server main file missing")

        # Check for tool categories
        categories = ['logs', 'system', 'database', 'performance', 'execution', 'optimization']
        found_categories = []

        for category in categories:
            category_dir = server_dir / category
            if category_dir.exists():
                tools = list(category_dir.glob('tools/*.py'))
                if tools:
                    found_categories.append(category)
                    self.results['components'][f'mcp_category_{category}'] = {
                        'status': 'healthy',
                        'message': f'{len(tools)} tools found'
                    }

        if found_categories:
            print(f"  ✅ Found {len(found_categories)} tool categories: {', '.join(found_categories)}")
        else:
            print("  ⚠️ No tool categories found")

    async def _check_token_efficiency(self):
        """Check token efficiency setup."""
        print("💰 Checking token efficiency setup...")

        # Check caching configuration
        cache_config = self.project_dir / 'config' / 'cache_config.json'
        if cache_config.exists():
            try:
                with open(cache_config) as f:
                    config = json.load(f)

                strategy = config.get('strategy', 'unknown')
                ttl = config.get('default_ttl', 0)
                max_size = config.get('max_size', 0)

                self.results['token_efficiency']['cache_config'] = {
                    'status': 'healthy',
                    'strategy': strategy,
                    'default_ttl': ttl,
                    'max_size': max_size
                }
                print(f"  ✅ Cache configured - Strategy: {strategy}, TTL: {ttl}s")
            except Exception as e:
                self.results['token_efficiency']['cache_config'] = {
                    'status': 'error',
                    'message': f'Invalid cache config: {e}'
                }
                print(f"  ❌ Cache config invalid: {e}")
        else:
            self.results['token_efficiency']['cache_config'] = {
                'status': 'warning',
                'message': 'Cache config not found'
            }
            print("  ⚠️ Cache config not found")

        # Check hook scripts for token efficiency
        pre_tool_hook = self.project_dir / 'hooks' / 'pre_tool_use' / 'advisor.sh'
        if pre_tool_hook.exists():
            with open(pre_tool_hook) as f:
                content = f.read()

            if 'token-saving' in content.lower() or 'token efficiency' in content.lower():
                self.results['token_efficiency']['pre_tool_hook'] = {
                    'status': 'healthy',
                    'message': 'Pre-tool-use hook includes token efficiency guidance'
                }
                print("  ✅ Pre-tool-use hook includes token efficiency guidance")
            else:
                self.results['token_efficiency']['pre_tool_hook'] = {
                    'status': 'warning',
                    'message': 'Pre-tool-use hook missing token efficiency guidance'
                }
                print("  ⚠️ Pre-tool-use hook missing token efficiency guidance")
        else:
            self.results['token_efficiency']['pre_tool_hook'] = {
                'status': 'warning',
                'message': 'Pre-tool-use hook not found'
            }

        # Estimate potential token savings
        estimated_savings = self._estimate_token_savings()
        self.results['token_efficiency']['estimated_savings'] = estimated_savings
        print(f"  📊 Estimated token savings: {estimated_savings}")

    def _estimate_token_savings(self) -> str:
        """Estimate potential token savings based on configuration."""
        components = self.results['components']

        # Count healthy components
        healthy_components = sum(1 for comp in components.values() if comp['status'] == 'healthy')
        total_components = len(components)

        if total_components == 0:
            return "Unable to estimate"

        # Base savings from healthy components
        base_savings = (healthy_components / total_components) * 70  # 70% base if all healthy

        # Bonus for specific components
        bonus = 0
        if 'mcp_server_main' in components and components['mcp_server_main']['status'] == 'healthy':
            bonus += 15  # MCP server adds 15%
        if 'cache_config' in self.results['token_efficiency'] and self.results['token_efficiency']['cache_config']['status'] == 'healthy':
            bonus += 10  # Cache config adds 10%

        total_savings = min(95, base_savings + bonus)  # Cap at 95%
        return f"{total_savings:.0f}%"

    def _calculate_overall_status(self):
        """Calculate overall system status."""
        components = self.results['components']
        total = len(components)

        if total == 0:
            self.results['overall_status'] = 'error'
            return

        healthy = sum(1 for comp in components.values() if comp['status'] == 'healthy')
        warnings = sum(1 for comp in components.values() if comp['status'] == 'warning')
        errors = sum(1 for comp in components.values() if comp['status'] == 'error')

        if errors == 0 and warnings == 0:
            self.results['overall_status'] = 'healthy'
        elif errors == 0:
            self.results['overall_status'] = 'warning'
        else:
            self.results['overall_status'] = 'error'

        self.results['summary'] = {
            'total_components': total,
            'healthy': healthy,
            'warnings': warnings,
            'errors': errors
        }

    def _generate_recommendations(self):
        """Generate improvement recommendations."""
        recommendations = []

        # Check for missing directories
        missing_dirs = [
            comp.replace('directory_', '') + '/'
            for comp, status in self.results['components'].items()
            if comp.startswith('directory_') and status['status'] != 'healthy'
        ]
        if missing_dirs:
            recommendations.append(f"Create missing directories: {', '.join(missing_dirs)}")

        # Check for missing configuration
        missing_configs = [
            comp.replace('config_', '')
            for comp, status in self.results['components'].items()
            if comp.startswith('config_') and status['status'] != 'healthy'
        ]
        if missing_configs:
            recommendations.append(f"Generate missing configuration files: {', '.join(missing_configs)}")

        # Check MCP server issues
        if 'mcp_server_main' in self.results['components'] and self.results['components']['mcp_server_main']['status'] != 'healthy':
            recommendations.append("Run MCP server setup: python scripts/setup_mcp_server.py")

        # Check hook system issues
        hook_issues = [
            comp for comp, status in self.results['components'].items()
            if comp.startswith('hook_') and status['status'] != 'healthy'
        ]
        if hook_issues:
            recommendations.append("Run hook generation: python scripts/generate_hooks.py")

        # Check token efficiency setup
        if self.results['token_efficiency'].get('cache_config', {}).get('status') != 'healthy':
            recommendations.append("Configure caching: python scripts/configure_caching.py --strategy smart")

        if self.results['token_efficiency'].get('pre_tool_hook', {}).get('status') != 'healthy':
            recommendations.append("Update pre-tool-use hook to include token efficiency guidance")

        self.results['recommendations'] = recommendations

    def print_results(self):
        """Print formatted health check results."""
        print("\n" + "="*60)
        print("🏥 HEALTH CHECK RESULTS")
        print("="*60)

        # Overall status
        status_emoji = {
            'healthy': '✅',
            'warning': '⚠️',
            'error': '❌',
            'unknown': '❓'
        }

        overall_status = self.results['overall_status']
        print(f"\nOverall Status: {status_emoji.get(overall_status, '❓')} {overall_status.upper()}")

        # Summary
        if 'summary' in self.results:
            summary = self.results['summary']
            print(f"\nComponents: {summary['healthy']}/{summary['total_components']} healthy")
            if summary['warnings'] > 0:
                print(f"Warnings: {summary['warnings']}")
            if summary['errors'] > 0:
                print(f"Errors: {summary['errors']}")

        # Token efficiency
        if 'estimated_savings' in self.results['token_efficiency']:
            savings = self.results['token_efficiency']['estimated_savings']
            print(f"\n💰 Estimated Token Savings: {savings}")

        # Component details
        print(f"\n📋 Component Details:")
        for comp_name, comp_data in self.results['components'].items():
            emoji = status_emoji.get(comp_data['status'], '❓')
            print(f"  {emoji} {comp_name}: {comp_data['message']}")

        # Recommendations
        if self.results['recommendations']:
            print(f"\n💡 Recommendations:")
            for i, rec in enumerate(self.results['recommendations'], 1):
                print(f"  {i}. {rec}")
        else:
            print(f"\n🎉 System is properly configured!")

        print("\n" + "="*60)

async def main():
    parser = argparse.ArgumentParser(description='Health check for token-efficient MCP & hook system')
    parser.add_argument('--project-dir', default='.',
                       help='Project directory to check')
    parser.add_argument('--output-format', choices=['text', 'json'],
                       default='text', help='Output format')
    parser.add_argument('--output-file', help='Output file for results')

    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    if not project_dir.exists():
        print(f"❌ Project directory does not exist: {project_dir}")
        sys.exit(1)

    checker = HealthChecker(project_dir)
    results = await checker.run_all_checks()

    if args.output_format == 'json':
        output = json.dumps(results, indent=2)
    else:
        checker.print_results()
        output = json.dumps(results, indent=2)

    if args.output_file:
        with open(args.output_file, 'w') as f:
            f.write(output)
        print(f"\n📄 Results saved to: {args.output_file}")

    # Exit with appropriate code
    if results['overall_status'] == 'error':
        sys.exit(1)
    elif results['overall_status'] == 'warning':
        sys.exit(2)
    else:
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())