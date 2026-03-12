#######################################################
#
# Nipype fMRI 1st Level Analysis tutorial for PSYC7250
# Professor: Stephanie Noble
#
# Guide: https://docs.google.com/document/d/1WC4bihzVXwzXBcKWGxSpqDKQ3XUU9h-7TiL58xZQdV0/edit#heading=h.n3roqcmzam5l
# Reference: https://miykael.github.io/nipype_tutorial/notebooks/handson_analysis.html
#
#######################################################

##### USER-DEFINED #####

course_dir = '/courses/PSYC5301.202630'
results_dir = course_dir+'/students/<your.student.id>/output/'


### Import Modules

from nipype import Node, Workflow

# Specify which SPM to use
from nipype.interfaces.matlab import MatlabCommand
MatlabCommand.set_default_paths('/shared/centos7/spm/12')
MatlabCommand.set_default_matlab_cmd('/opt/matlab/bin/matlab') # from the binding we set

from nipype.interfaces.fsl import Info
Info.version = lambda: "6.0" # from the version we saw in "flirt -version"


# Typically we would include all imports here, but for clarity in seeing what
# goes with what, we we do it at each step

## Set Paths

## Set Data Paths

data_dir = course_dir+'/data/ds000114-tutorial/'
tpm_img = course_dir+'/data/TPM.nii'

# example:
# results_dir = '/courses/PSYC7250.202430/staff/s.noble/output/'

# Create the workflow here
# Hint: use 'base_dir' to specify where to store the working directory
analysis1st = Workflow(name='work_1st', base_dir=results_dir)

# Import task timings into a specialized nipype object (a "Bunch")
# task timings include: stimuli onsets, duration, etc.

import pandas as pd
from nipype.interfaces.base import Bunch

# Import data
trialinfo = pd.read_table(data_dir+'task-fingerfootlips_events.tsv')

# Create task timing "Bunch"
conditions = []
onsets = []
durations = []

for group in trialinfo.groupby('trial_type'):
    conditions.append(group[0])
    onsets.append(list(group[1].onset -10)) # subtracting 10s due to removing of 4 dummy scans
    durations.append(group[1].duration.tolist())

subject_info = [Bunch(conditions=conditions,
                      onsets=onsets,
                      durations=durations,
                      )]



# Node: Store task and scan timing-related info

from nipype.algorithms.modelgen import SpecifySPMModel
# Initiate the SpecifySPMModel node here
modelspec = Node(SpecifySPMModel(concatenate_runs=False,
                                 input_units='secs',
                                 output_units='secs',
                                 time_repetition=2.5,
                                 high_pass_filter_cutoff=128,
                                 subject_info=subject_info),
                 name="modelspec")

# Create 1st-level contrasts (this won't actually be used until after we fit the timeseries model)

# Condition names
condition_names = ['Finger', 'Foot', 'Lips']

# Contrasts (single condition contrasts will contrast against 0)
# t = t-statistic, F = F-statistic
cont01 = ['average',        'T', condition_names, [1/3., 1/3., 1/3.]]
cont02 = ['Finger',         'T', condition_names, [1, 0, 0]]
cont03 = ['Foot',           'T', condition_names, [0, 1, 0]]
cont04 = ['Lips',           'T', condition_names, [0, 0, 1]]
cont05 = ['Finger < others','T', condition_names, [-1, 0.5, 0.5]]
cont06 = ['Foot < others',  'T', condition_names, [0.5, -1, 0.5]]
cont07 = ['Lips > others',  'T', condition_names, [-0.5, -0.5, 1]]

cont08 = ['activation',     'F', [cont02, cont03, cont04]]
cont09 = ['differences',    'F', [cont05, cont06, cont07]]

contrast_list = [cont01, cont02, cont03, cont04, cont05, cont06, cont07, cont08, cont09]



# Node: Create 1st level design matrix

# Decide how to model the hemodynamic response function (prespecified HRF, fourier, etc), autocorrelation, etc.

from nipype.interfaces.spm import Level1Design
# Initiate the Level1Design node here
level1design = Node(Level1Design(bases={'hrf': {'derivs': [1, 0]}},
                                 timing_units='secs',
                                 interscan_interval=2.5,
                                 model_serial_correlations='AR(1)'),
                    name="level1design")

# Connect node with SPM model node

analysis1st.connect([(modelspec, level1design, [('session_info',
                                                 'session_info')])])

# Node: Estimate model

from nipype.interfaces.spm import EstimateModel
# Initiate the EstimateModel node here
level1estimate = Node(EstimateModel(estimation_method={'Classical': 1}),
                      name="level1estimate")

# Connect node with 1st level design node

analysis1st.connect([(level1design, level1estimate, [('spm_mat_file',
                                                      'spm_mat_file')])])

# Node: Estimate contrasts

from nipype.interfaces.spm import EstimateContrast
# Initiate the EstimateContrast node here
level1conest = Node(EstimateContrast(contrasts=contrast_list),
                    name="level1conest")

# Connect to model estimation node
analysis1st.connect([(level1estimate, level1conest, [('spm_mat_file',
                                                      'spm_mat_file'),
                                                     ('beta_images',
                                                      'beta_images'),
                                                     ('residual_image',
                                                      'residual_image')])])

# Node: "Normalize" to common space

from nipype.interfaces.spm import Normalize12

# Location of the template
# typically TPM is in an SPM directory, e.g.,  /opt/spm12-r7219/spm12_mcr/spm12/tpm/TPM.nii, but we copied this image to data
# TODO: locate the official path
#template ='/courses/PSYC7250.202430/data/TPM.nii'
# Initiate the Normalize12 node here
normalize = Node(Normalize12(jobtype='estwrite',
                             tpm=template,
                             write_voxel_sizes=[4, 4, 4]
                            ),
                 name="normalize")

# Connect to constrast estimation node
analysis1st.connect([(level1conest, normalize, [('con_images',
                                                 'apply_to_files')])
                     ])

# Node: File selector

# Import the SelectFiles
from nipype import SelectFiles

# String template with {}-based strings
# TODO: check these paths
templates = {'anat': data_dir+'/sub-{subj_id}/ses-test/anat/sub-{subj_id}_ses-test_T1w.nii.gz',
             'func': results_dir+'/work_preproc/_subject_id_{subj_id}/detrend/detrend.nii.gz',
             'mc_param': results_dir+'/work_preproc/_subject_id_{subj_id}/mcflirt/asub-{subj_id}_ses-{ses_id}_task-{task_id}_bold_roi_mcf.nii.par',
             'outliers': results_dir+'/work_preproc/_subject_id_{subj_id}/art/art.asub-{subj_id}_ses-{ses_id}_task-{task_id}_bold_roi_mcf_outliers.txt'
            }

# Create SelectFiles node
sf = Node(SelectFiles(templates, sort_filelist=True),
          name='selectfiles')
sf.inputs.ses_id='test'
sf.inputs.task_id='fingerfootlips'

# list of subject identifiers
subject_list = ['02','04','07']
# subject_list = ['02', '03', '04', '07', '08', '09']
sf.iterables = [('subj_id', subject_list)]

# Node: Gunzip

# like before, SPM can only use unzipped niftis

from nipype.algorithms.misc import Gunzip
# Initiate the two Gunzip node here
gunzip_anat = Node(Gunzip(), name='gunzip_anat')
gunzip_func = Node(Gunzip(), name='gunzip_func')

# Connect file selector and gunzip nodes to the rest

analysis1st.connect([(sf, gunzip_anat, [('anat', 'in_file')]),
                     (sf, gunzip_func, [('func', 'in_file')]),
                     (gunzip_anat, normalize, [('out_file', 'image_to_align')]),
                     (gunzip_func, modelspec, [('out_file', 'functional_runs')]),
                     (sf, modelspec, [('mc_param', 'realignment_parameters'),
                                      ('outliers', 'outlier_files'),
                                      ])
                    ])

# Node: Data sink - get rid of unwanted intermediates / derivatives

from nipype.interfaces.io import DataSink

# Initiate DataSink node here
datasink = Node(DataSink(base_directory=results_dir,
                         container='datasink_handson'),
                name="datasink")

## Use the following substitutions for the DataSink output
substitutions = [('_subj_id_', 'sub-')]
datasink.inputs.substitutions = substitutions

# Connect nodes to datasink here
analysis1st.connect([(level1conest, datasink, [('spm_mat_file', '1stLevel.@spm_mat'),
                                               ('spmT_images', '1stLevel.@T'),
                                               ('spmF_images', '1stLevel.@F'),
                                              ]),
                     (normalize, datasink, [('normalized_files', 'normalized.@files'),
                                            ('normalized_image', 'normalized.@image'),
                                           ]),
                    ])

# Visualize workflow

# Create 1st-level analysis output graph
# analysis1st.write_graph(graph2use='colored', format='png', simple_form=False)

# Visualize the graph
# from IPython.display import Image
# Image(filename=results_dir+'work_1st/graph.png')

# # Run

analysis1st.run('MultiProc', plugin_args={'n_procs': 8})

