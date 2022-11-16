#!/bin/bash

#SBATCH -N 1
#SBATCH -n 5
#SBATCH -p gpu 
#SBATCH --gres=gpu:2
#SBATCH --no-requeue
#SBATCH --output=mpt_imagenet.out

source activate py37_coop

PROJ_PATH="/data01/home/scy0037/run/myz/MuDPT"
DATA="${PROJ_PATH}/datasets"
TRAINER="MPT"

CFG="vit_b16_c2_ep5_batch4"
BACKBONE_PATH="${PROJ_PATH}/pretrained/ViT-B-16.pt"
DATASET="imagenet"
DEEP_TEXT_N_CTX=2
DEEP_IMG_N_CTX=2
TEXT_PROMPT_DEPTH=12
IMG_PROMPT_DEPTH=12
SHOTS=16
SEED=2

DIR=output/${DATASET}/${CFG}_${SHOTS}shots/tnctx${DEEP_TEXT_N_CTX}_vnvtx${DEEP_IMG_N_CTX}_tdepth${TEXT_PROMPT_DEPTH}_vdepth${IMG_PROMPT_DEPTH}/seed${SEED}

if [ -d "$DIR" ]; then
    echo "Oops! The results exist at ${DIR} (so skip this job)"
else
    python ${PROJ_PATH}/train.py \
    --dataset_root ${DATA} \
    --output_dir ${DIR} \
    --seed ${SEED} \
    --trainer ${TRAINER} \
    --trainer_config "${PROJ_PATH}/configs/trainers/${TRAINER}/${CFG}.yaml" \
    --dataset_config "${PROJ_PATH}/configs/datasets/${DATASET}.yaml" \
    DATASET.NUM_SHOTS ${SHOTS} \
    MODEL.BACKBONE.PATH ${BACKBONE_PATH}
fi