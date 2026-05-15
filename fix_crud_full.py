with open('app/crud.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Разделитель до и после класса ProjectUserCRUD
before_class = content.split('class ProjectUserCRUD')[0]
after_class = content.split('# Заменяем стандартные классы')[1]

new_class = '''class ProjectUserCRUD(CRUDBase[models.ProjectUser]):
    def check_access(self, db: Session, user_id: int, project_id: int) -> bool:
        """Проверить доступ пользователя к проекту (включая владельца и shared проекты)"""
        # Проверка, является ли пользователь владельцем
        project = db.query(models.Project).filter(models.Project.id == project_id).first()
        if project and project.owner_id == user_id:
            return True
        
        # Проверка через ProjectUser
        has_user_access = db.query(models.ProjectUser).filter(
            models.ProjectUser.user_id == user_id,
            models.ProjectUser.project_id == project_id
        ).first() is not None
        
        if has_user_access:
            return True
        
        # Проверка через ProjectShare
        has_share_access = db.query(models.ProjectShare).filter(
            models.ProjectShare.shared_with_id == user_id,
            models.ProjectShare.project_id == project_id
        ).first() is not None
        
        return has_share_access
    
    def get_user_projects(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[models.Project]:
        """Получить все проекты пользователя (владельца, участника и shared)"""
        # Проекты, где пользователь является владельцем
        owned_projects = db.query(models.Project).filter(
            models.Project.owner_id == user_id
        ).offset(skip).limit(limit).all()
        
        # Проекты, где пользователь является участником
        user_projects = db.query(models.Project).join(
            models.ProjectUser, models.Project.id == models.ProjectUser.project_id
        ).filter(
            models.ProjectUser.user_id == user_id
        ).offset(skip).limit(limit).all()
        
        # Проекты, доступные через sharing
        shared_projects = db.query(models.Project).join(
            models.ProjectShare, models.Project.id == models.ProjectShare.project_id
        ).filter(
            models.ProjectShare.shared_with_id == user_id
        ).offset(skip).limit(limit).all()
        
        # Объединяем и убираем дубликаты
        all_projects = {p.id: p for p in owned_projects + user_projects + shared_projects}
        return list(all_projects.values())


'''

new_content = before_class + new_class + '# Заменяем стандартные классы' + after_class

with open('app/crud.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('crud.py restored successfully!')
