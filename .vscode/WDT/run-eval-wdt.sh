EVAL_values=/home/sj/BA_stuff/BA_evaluate/ipal-revaluate
EVAL_graph=/home/sj/BA_stuff/BA_evaluate/ipal-plot-alerts
ids_outputs=/home/sj/BA_stuff/transcribed_pcaps/WDT/ids_out
out=/home/sj/BA_stuff/transcribed_pcaps/WDT/evaluate
attacks=/home/sj/BA_stuff/datasets/WDT/attacks.json
bashlog=$out/bash.log

for filename in $ids_outputs/*.out; do 
    echo "start evaluating $(basename filename)" >> $bashlog
    $EVAL_values \
        --output $out/$(basename filename).out \
        --attacks $attacks \
        --timed-dataset true \
        --log INFO \
        --logfile $out/$(basename filename).log \
        $filename;
    echo "finished evaluating $(basename filename)" >> $bashlog
    echo "start plotting $(basename $filename)" >> $bashlog

    $EVAL_graph \
        --output $out/$(basename $filename).picture \
        --attacks $attacks \
        --dataset "WDT" \
        --title $(basename $filename) \
        --log INFO \
        --logfile $out/$(basename $filename).picture.log \
        $filename;

    echo "finished plotting $(basename $filename)" >> $bashlog
done
