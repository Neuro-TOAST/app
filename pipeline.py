import BatchParcelation
import BatchSlidingWindow
import BatchClustering
import BatchAnalyseStates

def define_pipeline():
    item_params = UIConfigItem('fMRI params', TypePassParent(), eid='fMRI')
    item_params.add(UIConfigItem('TR', TypeFloatNumber()))

    item_parcelation = UIConfigItem('Parcelation', TypeEnabled())
    item_parcelation.runnable = BatchParcelation.BatchParcelation
    # parcelation_choice = item_parcelation.add_choice()
    # aal = parcelation_choice.add('AAL atlas')
    # aal.add(UIConfigItem('Atlas', TypeCombo(['Select', 'AAL', 'HCP'])))
    # aal.add(UIConfigItem('Excluded indexes', TypeText()))
    # networks = parcelation_choice.add('Networks')
    # networks.add(UIConfigItem('Config file', TypeText()))

    item_parcelation.add(UIConfigItem('Method', TypeCombo(['Select', 'AAL', 'Gao'])))
    item_parcelation.add(UIConfigItem('Excluded indexes', TypeText()))

    item_sliding_window = UIConfigItem('Sliding window', TypeEnabled(), eid='sliding-window')
    item_sliding_window.runnable = BatchSlidingWindow.BatchSlidingWindow
    item_sliding_window.add(UIConfigItem('wsize', TypeNumber()))
    item_sliding_window.add(UIConfigItem('wstep', TypeNumber()))

    item_clustering = UIConfigItem('KMeans', TypeEnabled())
    item_clustering.runnable = BatchClustering.BatchClustering
    item_clustering.add(UIConfigItem('Source', TypeText(), eid='source'))
    item_clustering.add(UIConfigItem('clusters-from', TypeNumber()))
    item_clustering.add(UIConfigItem('clusters-to', TypeNumber()))

    item_states = UIConfigItem('Analyse states', TypeEnabled(), eid='analyse-states')
    item_states.runnable = BatchAnalyseStates.BatchAnalyseStates
    item_states.add(UIConfigItem('clusters-selected', TypeNumber()))

    item_pipeline = UIConfigItem('', TypePassParent())
    item_pipeline.add(item_params)
    item_pipeline.add(item_parcelation)
    item_pipeline.add(item_sliding_window)
    item_pipeline.add(item_clustering)
    item_pipeline.add(item_states)
    return item_pipeline

class TypePassParent:
    def __init__(self):
        self.type = 'pass'
        self.value_type = 'readonly'

class TypeEnabled:
    def __init__(self):
        self.type = 'enabled'
        self.value_type = 'readonly'

class TypeNumber:
    def __init__(self):
        self.type = 'number'
        self.value_type = 'number'

class TypeFloatNumber:
    def __init__(self):
        self.type = 'float_number'
        self.value_type = 'number'

class TypeText:
    def __init__(self):
        self.type = 'text'
        self.value_type = 'text'

class TypeCombo:
    def __init__(self, options):
        self.type = 'combo'
        self.options = options
        self.value_type = 'combo'

class UIConfigItem:
    def __init__(self, text, _type, eid=''):
        self.eid = eid
        self.label = text
        self.type = _type
        self.children = []
        self.parent = None
        self.value = None
        self.runnable = None
        self.tree_item = None

    def get_id(self):
        return self.eid if self.eid else self.label

    def add(self, child):
        child.parent = self
        self.children.append(child)

    def get_label(self):
        return self.label

    def get_value(self):
        if self.type.type == 'float_number':
            return float(self.value)
        elif self.type.type == 'number':
            return int(self.value)
        else:
            return self.value

    def get_children(self):
        return self.children

    def set_value(self, value):
        self.value = value
        self.tree_item.setText(1, self.value)

    def is_runnable(self):
        return self.runnable is not None

    # TODO: funguje jen v jedne urovni
    def get_params(self):
        params = {}
        for child in self.children:
            params[child.get_id()] = child.get_value()
        return params
