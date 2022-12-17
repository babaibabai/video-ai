"""
Let's pull out some pieces of this to generalize it beyond this specific notebook a bit more.
Also... let's move most of the remainint logic out of the notebook. cause... ugh.

Anyway, idea with this module is to provide a generic, opinionated project layout to facilitate
- designing notebooks with shared tooling and features, specifically robust resume
- reusing models
"""
from collections import defaultdict
from omegaconf import OmegaConf, DictConfig
from pathlib import Path
import time
from warnings import warn
from loguru import logger


class Configable:
    def __init__(
        self, 
        name=None, 
        root=None,
        config_name='config.yaml',
        **kwargs
    ):
        self.config_name = config_name
        self.name = name

        if root is None:
            root = Path('.')
        self.root = root
        
        # @property attributes constructed from attributes above
        self.root.mkdir(exist_ok=True, parents=True)
        self.load(**kwargs)

    @property
    def cfg_fpath(self):
        return self.root / self.config_name

    @property
    def cfg(self):
        if not hasattr(self, '_cfg'):
            raise ValueError(
                "You should never see this error. Something's wrong."
                "The _cfg attribute is not present on the class. This attribute "
                "should have been attached by the __init__ method or the load() method. "
                "Maybe the attribute was somehow deleted from the class? Please file an issue and/or message @DigThatData"
                "and explain the circumstances under which you saw this message."
            )
            #self._cfg = self.to_config()
        return self._cfg

    def to_config(self, extra_params):
        _d = {
            'name':self.name,
            'root':str(self.root),
        }
        cfg = OmegaConf.create(_d)
        logger.debug(cfg)
        logger.debug(extra_params)
        cfg.update(extra_params)
        logger.debug(cfg)
        return cfg
    
    def reload(self):
        """Alias for the load() method"""
        self.load()

    def load(self, **kwargs):
        if self.cfg_fpath.exists():
            self.load_existing(**kwargs)
        else:
            logger.debug(kwargs)
            self._cfg = self.to_config(kwargs)
            self.checkpoint()
    
    def load_existing(self, **kwargs):
        if kwargs:
            warn(
                f"Config file {str(self.cfg_fpath)} already exists, extra initialization arguments will be ignored in favor of persisted values."
                "To override the persisted values, run .update(...).checkpoint() after loading the project."
                f"ignored arguments: {kwargs}"
                )
        logger.debug(f"loading {self.cfg_fpath}")
        with self.cfg_fpath.open() as f:
            self._cfg = OmegaConf.load(f)
    
    def checkpoint(self):
        # do something special if already exists to permit rollback? maybe track file in its own little git?
        with self.cfg_fpath.open('w') as f:
            OmegaConf.save(config=self.cfg, f=f)


class Project(Configable):
    def __init__(
        self, 
        name=None, 
        parent=None, 
        config_name='config.yaml',
        **kwargs
    ):
        logger.debug(name)
        if parent is None:
            parent = Path('.')
        if not isinstance(parent, Path):
            parent = Path(parent)
        if not name:
            name = self.generate_new_project_name()
        root = parent / name
        super().__init__(
            name=name,
            root=root,
            config_name=config_name,
            **kwargs,
        )
    
    @staticmethod
    def generate_new_project_name():
        return str(time.time())


class ProjectVktrs(Project):
    def __init__(self, name, parent, config_name='storyboard.yaml', **kwargs):
        super().__init__(name=name, parent=parent, config_name=config_name, **kwargs)


projects_by_type = defaultdict(lambda: Project)
projects_by_type['vktrs'] = ProjectVktrs


class Workspace(Configable):
    def __init__(
        self,
        cfg_path='workspace_config.yaml',
        active_project_name=None, # project name 
        project_root=None, # where to find the project
        gdrive_mounted='', # motivation here is for use with colab
        model_dir='', # want to make it possible for users to share models across process. save on setup time and storage space.
        #output_dir'', # ok.. maybe this one should be in the project setup and not the workspace. more portable projects this way I guess?
        # nah, output dir should be a project config
        project_type=None,
        **kwargs
    ):
        logger.debug(active_project_name)
        super().__init__(
            config_name=cfg_path,
            root=project_root,
            ####################
            gdrive_mounted=gdrive_mounted,
            model_dir=model_dir,
            project_type=project_type,
            active_project_name=active_project_name,
        )
        logger.debug(self.cfg)
        logger.debug(self.cfg.active_project_name)
        #self.load()

    def load(self, **kwargs):
        if self.cfg_fpath.exists():
            self.load_existing(**kwargs)
        else:
            logger.debug(kwargs)
            self._cfg = self.to_config(kwargs)
            if self._cfg.active_project_name:
                self.activate_project()
            self.checkpoint()

    def load_existing(self, **kwargs):
        logger.debug(f"loading {self.cfg_fpath}")
        with self.cfg_fpath.open() as f:
            self._cfg = OmegaConf.load(f)
        self._cfg.update(kwargs)
        self.activate_project()
        self.checkpoint()

    def activate_project(self, name=None):
        if not name:
            name = self.cfg.active_project_name
        ProjectFactory = projects_by_type[self.cfg.root]
        self.active_project = ProjectFactory(name, self.cfg.root)
        self._cfg.update({"active_project":self.active_project.cfg})
        logger.debug(self._cfg)

    def checkpoint(self):
        super().checkpoint()
        if hasattr(self, 'active_project'):
            self.active_project.checkpoint()

