"""
Tag Manager Module for MEGA Account Generator
Handles account tagging and tag operations
"""
import csv_utils


class TagManager:
    """Manage tags for accounts"""
    
    @staticmethod
    def get_account_tags(email):
        """
        Get tags for a specific account.
        
        Args:
            email: Account email address
            
        Returns:
            list: Tags for the account
        """
        if not csv_utils.csv_exists():
            return []
        
        rows = csv_utils.read_accounts()
        
        for row in rows:
            if row and row[0] == email:
                # Tags are in column 5 (index 5)
                if len(row) > 5 and row[5]:
                    return [tag.strip() for tag in row[5].split(',') if tag.strip()]
                return []
        
        return []
    
    @staticmethod
    def set_account_tags(email, tags):
        """
        Set tags for an account.
        
        Args:
            email: Account email address
            tags: List of tag strings
        """
        if not csv_utils.csv_exists():
            return False
        
        rows = csv_utils.read_accounts()

        if not rows:
            return False
        
        updated = False
        for i in range(len(rows)):
            if rows[i] and rows[i][0] == email:
                # csv_utils.read_accounts ensures 8 columns
                rows[i][5] = ','.join(tags)
                updated = True
                break
        
        if updated:
            csv_utils.write_accounts(rows)
        
        return updated
    
    @staticmethod
    def add_tag(email, tag):
        """
        Add a tag to an account.
        
        Args:
            email: Account email
            tag: Tag to add
        """
        current_tags = TagManager.get_account_tags(email)
        if tag and tag not in current_tags:
            current_tags.append(tag)
            return TagManager.set_account_tags(email, current_tags)
        return False
    
    @staticmethod
    def remove_tag(email, tag):
        """
        Remove a tag from an account.
        
        Args:
            email: Account email
            tag: Tag to remove
        """
        current_tags = TagManager.get_account_tags(email)
        if tag in current_tags:
            current_tags.remove(tag)
            return TagManager.set_account_tags(email, current_tags)
        return False
    
    @staticmethod
    def get_all_tags():
        """
        Get all unique tags across all accounts.
        
        Returns:
            list: Sorted list of unique tags
        """
        if not csv_utils.csv_exists():
            return []
        
        tags_set = set()
        
        rows = csv_utils.read_accounts()
            
        for row in rows:
            if row and len(row) > 5 and row[5]:
                account_tags = [tag.strip() for tag in row[5].split(',') if tag.strip()]
                tags_set.update(account_tags)
        
        return sorted(list(tags_set))
    
    @staticmethod
    def get_accounts_by_tag(tag):
        """
        Get all accounts that have a specific tag.
        
        Args:
            tag: Tag to search for
            
        Returns:
            list: Email addresses with the tag
        """
        if not csv_utils.csv_exists():
            return []
        
        matching = []
        
        rows = csv_utils.read_accounts()
            
        for row in rows:
            if row and len(row) > 5 and row[5]:
                account_tags = [t.strip() for t in row[5].split(',') if t.strip()]
                if tag in account_tags:
                    matching.append(row[0])
        
        return matching
