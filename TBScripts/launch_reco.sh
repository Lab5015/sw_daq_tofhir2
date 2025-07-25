FIRST=$1
LAST=$2
for run in `seq $FIRST 1 $LAST`;
do
   echo $run
#   ./convert.py --config ../config_19.00/config_ith1_ith2_ithE.ini --mode e -r ${run} --refChannels 64,65,66,67,92,93,94,95,96;
   ./convert.py --config ../config/config_ith1_ith2_ithE.ini --mode e -r ${run} --refChannels 64,65,66,67,92,93,94,95,96;
#   ./convert.py --config ../config_10.01/config_ith1_ith2_ithE.ini --mode e -r ${run} --refChannels 64,65,66,67,92,93,94,95,96;
#   ./convert.py --config ../config/config_ith1_ith2_ithE.ini --mode e -r ${run}

#   ./convert.py --config ../config/config_ith1.ini --mode s -r ${run}
done

#COMMAND="parallel --bar --jobs 4 ./convert.py  --config ../config/config_ith1_ith2_ithE.ini --refChannels 64,65,66,67,92,93,94,95,96 --mode e -r ::: "
#for (( i=$1; i<$2+1; i++)); do COMMAND=$COMMAND" "$i; done;
#
#echo $COMMAND
#$COMMAND

