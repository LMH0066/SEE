import logging

import numpy as np
import torch
import torch.utils.data as data

from util import mat2array


class Dataset(data.Dataset):
    '''
    Reading the training single-cell hic dataset
    '''
    def __init__(self, file_path, is_train=False):
        super(Dataset, self).__init__()

        self.is_train = is_train
        self._get_data(file_path)
        
        logger = logging.getLogger('base')
        logger.info('Dataset is created.')

    def _get_data(self, file_path):
        '''
        [
            {
                'scRNA': np.array(),
                'scRNA_head': [], 
                'scHiC': 
                {
                    'gene_name': np.array(),
                    ...
                }
            },
            ...
        ]
        '''
        def _crack(integer):
            start = int(np.sqrt(integer))
            factor = integer / start
            while int(factor) != factor:
                start += 1
                factor = integer / start
            return int(factor), start

        _datas = np.load(file_path, allow_pickle=True)

        # self._scRNA_data = [_data['scRNA'].reshape(_crack(_data['scRNA'].shape[0])) for _data in _datas]

        self._scRNA_data, self._scHiC_data = [], []
        # scHiC_head = None
        for _data in _datas:
            _scHiC_data = mat2array(_data['scHiC']['ABCB1'])
            # _scHiC_data = np.log1p(_scHiC_data)
            if np.all(_scHiC_data == 0):
                continue
            self._scHiC_data.append(_scHiC_data)

            _len = int(_data['scRNA'].shape[0] / 64)
            _input_size = tuple([ i * 8 for i in _crack(_len)])
            self._scRNA_data.append(np.array(_data['scRNA'][:_len*64].reshape(_input_size)))
            # scHiC_head = _data['scHiC'].keys() if scHiC_head is None else scHiC_head
            # _scHiC_data = None
            # for gene_name in scHiC_head:
            #     _gene_scHiC_data = _data['scHiC'][gene_name].flatten()
            #     _scHiC_data = _gene_scHiC_data if _scHiC_data is None else np.concatenate((_scHiC_data, _gene_scHiC_data))

        self._scRNA_data = np.array(self._scRNA_data, dtype='float32')
        self._scHiC_data = np.array(self._scHiC_data, dtype='float32')

    def __getitem__(self, index):
        input_tensor = torch.as_tensor(self._scRNA_data[index])
        target_tensor = torch.as_tensor(self._scHiC_data[index]) if self.is_train else torch.as_tensor([])
        return input_tensor, target_tensor

    def __len__(self):
        return len(self._scRNA_data)

    def slice(self, index):
        self._scRNA_data = self._scRNA_data[index]
        self._scHiC_data = self._scHiC_data[index]
