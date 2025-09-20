"""
Device Data Parser Module
Cleans and structures data scraped from FDA TPLC database.
"""

import logging
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class DeviceDataParser:
    """Parser for cleaning and structuring scraped device data"""
    
    def __init__(self):
        pass
    
    def parse_device_data(self, raw_device_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and clean raw device data from scraper.
        
        Args:
            raw_device_data: Raw data dictionary from scraper
            
        Returns:
            Clean, structured device data
        """
        
        try:
            device_name = self._clean_device_name(raw_device_data.get('device_name', 'Unknown Device'))
            
            # Parse device problems
            device_problems = self._parse_problems(
                raw_device_data.get('device_problems', []),
                problem_type='device'
            )
            
            # Parse patient problems  
            patient_problems = self._parse_problems(
                raw_device_data.get('patient_problems', []),
                problem_type='patient'
            )
            
            # Create structured response
            parsed_data = {
                'device_name': device_name,
                'device_url': raw_device_data.get('url', ''),
                'device_problems': device_problems,
                'patient_problems': patient_problems,
                'total_device_problems': len(device_problems),
                'total_patient_problems': len(patient_problems),
                'summary': self._create_summary(device_name, device_problems, patient_problems)
            }
            
            logger.info(f"Parsed device: {device_name} with {len(device_problems)} device problems and {len(patient_problems)} patient problems")
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"Error parsing device data: {e}")
            # Return minimal structure on error
            return {
                'device_name': 'Parse Error',
                'device_url': raw_device_data.get('url', ''),
                'device_problems': [],
                'patient_problems': [],
                'total_device_problems': 0,
                'total_patient_problems': 0,
                'error': str(e)
            }
    
    def _clean_device_name(self, device_name: str) -> str:
        """Clean and normalize device name"""
        
        if not device_name or device_name.strip() == '':
            return 'Unknown Device'
        
        # Remove extra whitespace and normalize
        cleaned = re.sub(r'\s+', ' ', device_name.strip())
        
        # Remove common prefixes/suffixes that don't add value
        cleaned = re.sub(r'^(Device:|Product:|Name:)\s*', '', cleaned, flags=re.IGNORECASE)
        
        return cleaned
    
    def _parse_problems(self, problems_list: List[Dict[str, Any]], problem_type: str) -> List[Dict[str, Any]]:
        """
        Parse and clean problems list.
        
        Args:
            problems_list: Raw problems from scraper
            problem_type: 'device' or 'patient'
            
        Returns:
            Cleaned problems list
        """
        
        parsed_problems = []
        
        for problem in problems_list:
            try:
                cleaned_problem = self._clean_single_problem(problem, problem_type)
                if cleaned_problem:
                    parsed_problems.append(cleaned_problem)
            except Exception as e:
                logger.warning(f"Error parsing problem {problem}: {e}")
                continue
        
        # Sort by count (highest first) and then by name
        parsed_problems.sort(key=lambda x: (-x['count'], x['problem_name']))
        
        return parsed_problems
    
    def _clean_single_problem(self, problem: Dict[str, Any], problem_type: str) -> Optional[Dict[str, Any]]:
        """Clean a single problem entry"""
        
        problem_name = problem.get('problem_name', '').strip()
        count = problem.get('count', 0)
        maude_link = problem.get('maude_link', '').strip()
        
        # Skip empty or invalid problems
        if not problem_name or problem_name.lower() in ['', 'n/a', 'none', 'null']:
            return None
        
        # Clean problem name
        problem_name = self._clean_problem_name(problem_name)
        
        # Validate and clean count
        count = self._clean_count(count)
        
        # Validate MAUDE link
        maude_link = self._clean_maude_link(maude_link)
        
        return {
            'problem_name': problem_name,
            'count': count,
            'maude_link': maude_link,
            'problem_type': problem_type
        }
    
    def _clean_problem_name(self, name: str) -> str:
        """Clean and normalize problem name"""
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', name.strip())
        
        # Remove common noise
        cleaned = re.sub(r'^(Problem:|Issue:|Type:)\s*', '', cleaned, flags=re.IGNORECASE)
        
        # Capitalize appropriately
        if cleaned.islower():
            cleaned = cleaned.title()
        
        return cleaned
    
    def _clean_count(self, count) -> int:
        """Clean and validate count value"""
        
        if isinstance(count, int):
            return max(0, count)
        
        if isinstance(count, str):
            # Extract number from string
            match = re.search(r'\d+', count)
            if match:
                return int(match.group())
        
        return 0
    
    def _clean_maude_link(self, link: str) -> str:
        """Clean and validate MAUDE link"""
        
        if not link:
            return ""
        
        # Ensure it's a proper URL
        if not link.startswith('http'):
            if link.startswith('/'):
                link = "https://www.accessdata.fda.gov" + link
            else:
                link = "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfmaude/" + link
        
        # Validate it looks like a MAUDE link
        if 'maude' not in link.lower():
            logger.warning(f"Link doesn't appear to be a MAUDE link: {link}")
        
        return link
    
    def _create_summary(self, device_name: str, device_problems: List[Dict], patient_problems: List[Dict]) -> Dict[str, Any]:
        """Create a summary of the device data"""
        
        # Calculate totals
        total_device_reports = sum(p['count'] for p in device_problems)
        total_patient_reports = sum(p['count'] for p in patient_problems)
        
        # Find most common problems
        top_device_problem = device_problems[0]['problem_name'] if device_problems else None
        top_patient_problem = patient_problems[0]['problem_name'] if patient_problems else None
        
        summary = {
            'device_name': device_name,
            'total_device_problem_reports': total_device_reports,
            'total_patient_problem_reports': total_patient_reports,
            'total_problems_tracked': len(device_problems) + len(patient_problems),
            'most_common_device_problem': top_device_problem,
            'most_common_patient_problem': top_patient_problem
        }
        
        # Add safety assessment
        if total_device_reports + total_patient_reports > 100:
            summary['safety_note'] = "High number of reported problems - review recommended"
        elif total_device_reports + total_patient_reports > 20:
            summary['safety_note'] = "Moderate number of reported problems"
        else:
            summary['safety_note'] = "Low number of reported problems"
        
        return summary
    
    def validate_response(self, parsed_data: Dict[str, Any]) -> bool:
        """
        Validate that parsed data meets API requirements.
        
        Args:
            parsed_data: Parsed device data
            
        Returns:
            True if valid, False otherwise
        """
        
        required_fields = ['device_name', 'device_url', 'device_problems', 'patient_problems']
        
        # Check required fields exist
        for field in required_fields:
            if field not in parsed_data:
                logger.error(f"Missing required field: {field}")
                return False
        
        # Validate problems structure
        for problem_list in [parsed_data['device_problems'], parsed_data['patient_problems']]:
            if not isinstance(problem_list, list):
                logger.error("Problems must be lists")
                return False
            
            for problem in problem_list:
                if not isinstance(problem, dict):
                    logger.error("Each problem must be a dictionary")
                    return False
                
                required_problem_fields = ['problem_name', 'count', 'maude_link']
                for field in required_problem_fields:
                    if field not in problem:
                        logger.error(f"Missing problem field: {field}")
                        return False
        
        return True
    
    def format_for_api_response(self, devices_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Format multiple devices data for final API response.
        
        Args:
            devices_data: List of parsed device data
            
        Returns:
            Formatted API response
        """
        
        # Validate all devices
        valid_devices = [device for device in devices_data if self.validate_response(device)]
        
        # Calculate aggregate statistics
        total_device_problems = sum(len(device['device_problems']) for device in valid_devices)
        total_patient_problems = sum(len(device['patient_problems']) for device in valid_devices)
        total_reports = sum(
            sum(p['count'] for p in device['device_problems']) + 
            sum(p['count'] for p in device['patient_problems'])
            for device in valid_devices
        )
        
        response = {
            'devices': valid_devices,
            'aggregate_summary': {
                'total_devices_analyzed': len(valid_devices),
                'total_device_problem_types': total_device_problems,
                'total_patient_problem_types': total_patient_problems,
                'total_reports_across_devices': total_reports
            }
        }
        
        return response