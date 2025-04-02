from django.core.management.base import BaseCommand
from django.shortcuts import get_object_or_404

from yeastphenome.apps.datasets.models import Dataset

import os
import sys

from yeastphenome.settings import (
     PATH_TO_SAFE,
     PATH_TO_SAFE_DATA,
     PATH_TO_SAFE_OUTPUT
)
sys.path.append(PATH_TO_SAFE)

import pandas as pd
from safepy import safe



class Command(BaseCommand):

    def add_arguments(self, parser):
            # Positional argument
            parser.add_argument('dataset_id', type=int, help='Dataset ID')

            # # Optional argument
            # parser.add_argument('--delete', action='store_true', help='Delete the file after processing')

    def handle(self, *args, **options):

        path_to_safe_data = PATH_TO_SAFE_DATA
        dataset_id = options['dataset_id']
        
        path_to_output_folder = PATH_TO_SAFE_OUTPUT
        output_file_name = '%d.jpg' % dataset_id
        path_to_output_file = os.path.join(path_to_output_folder, output_file_name)

        sf = safe.SAFE(path_to_safe_data=path_to_safe_data)
        sf.load_network(network_file='networks/Costanzo_Science_2016.gpickle')
        sf.define_neighborhoods()

        dataset = get_object_or_404(Dataset, id=dataset_id)
        print(dataset)
        data = pd.DataFrame(dataset.get_scores())
        print(data.head())

        data.set_index('gene_systematic_name', inplace=True)
        sf.load_attributes(attribute_file=data[['valuez']])

        sf.compute_pvalues(num_permutations=1000)

        sf.plot_sample_attributes(show_network=False, 
            show_costanzo2016=True, 
            show_costanzo2016_clabels=True,
            show_title=False, 
            save_fig=path_to_output_file)

        # super(Command, self).handle(*args, **options)

        # all_datasets = Dataset.objects.all_loaded()

        # for dataset in all_datasets:

        #     pass

        self.stdout.write('Done')
