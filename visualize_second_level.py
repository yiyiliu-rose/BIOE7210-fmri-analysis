# # Visualize results

from nilearn.plotting import plot_glass_brain

##### USER-DEFINED #####

course_dir = '/courses/PSYC5301.202630'
results_dir = course_dir+'/students/liu.yiyi3/output/'
img_path = results_dir + 'work_2nd/_cont_id_0005/level2thresh/spmT_0001_thr.nii' # thresholded contrast
out_filename = results_dir + "glass_brain_contrast.png"

# other images
# img_path = results_dir + 'datasink_handson/2ndLevel/con_0002/spmT_0001_thr.nii' # same as above
# img_path = results_dir + 'work_2nd/_cont_id_0008/level2conestimate/spmT_0001.nii' # full contrast image
# img_path = results_dir + 'work_2nd/_cont_id_0004/level2estimate/beta_0001.nii' # beta image (pre-contrast)


## Plot

display = plot_glass_brain(img_path, display_mode='lyrz',
                 black_bg=True, colorbar=True, vmax=11)

display.savefig(out_filename, dpi=300)
display.close()


## Explore characteristics

#import numpy as np
#import nibabel as nib
#my_img = nib.load(img_path)
#data = my_img.get_fdata()
#np.count_nonzero(data)


