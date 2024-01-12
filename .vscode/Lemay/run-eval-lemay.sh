EVAL_values=/home/sj/BA_stuff/BA_evaluate/ipal-evaluate
EVAL_graph=/home/sj/BA_stuff/BA_evaluate/ipal-plot-alerts
ids_outputs=/home/sj/BA_stuff/transcribed_pcaps/Lemay/ids_out
eval_out=/home/sj/BA_stuff/transcribed_pcaps/Lemay/evaluate
graph_out=/home/sj/BA_stuff/transcribed_pcaps/Lemay/graph
attacks=/home/sj/BA_stuff/datasets/Lemay/
bashlog=/home/sj/BA_stuff/transcribed_pcaps/Lemay/eval_graph_bash.log

# characterization
for filename in $ids_outputs/characterization_*.out; do 
    echo "start evaluating $(basename $filename)" >> $bashlog
    $EVAL_values \
        --output $eval_out/$(basename $filename).out \
        --attacks $attacks/attacks-characterization_modbus_6RTU_with_operate.json \
        --timed-dataset true \
        --log INFO \
        --logfile $eval_out/$(basename $filename).log \
        $filename;
    
    echo "finished evaluating $(basename $filename)" >> $bashlog
    echo "start plotting $(basename $filename)" >> $bashlog

    $EVAL_graph \
        --output $eval_out/$(basename $filename).picture \
        --attacks $attacks/attacks-characterization_modbus_6RTU_with_operate.json \
        --dataset "Lemay 6RTU" \
        --title "Lemay 6RTU $(basename $filename)" \
        --log INFO \
        --logfile $eval_out/$(basename $filename).picture.log \
        $filename;

    echo "finished plotting $(basename $filename)" >> $bashlog
done

# CNC Upload
for filename in $ids_outputs/CnC_upload_*.out; do 
    echo "start evaluating $(basename $filename)" >> $bashlog
    $EVAL_values \
        --output $eval_out/$(basename $filename).out \
        --attacks $attacks/attacks-CnC_uploading_exe_modbus_6RTU_with_operate.json \
        --timed-dataset true \
        --log INFO \
        --logfile $eval_out/$(basename $filename).log \
        $filename;

    echo "finished evaluating $(basename $filename)" >> $bashlog
    echo "start plotting $(basename $filename)" >> $bashlog

    $EVAL_graph \
        --output $eval_out/$(basename $filename).picture \
        --attacks $attacks/attacks-CnC_uploading_exe_modbus_6RTU_with_operate.json \
        --dataset "Lemay 6RTU" \
        --title "Lemay 6RTU $(basename $filename)" \
        --log INFO \
        --logfile $eval_out/$(basename $filename).picture.log \
        $filename;

    echo "finished plotting $(basename $filename)" >> $bashlog
done

# Exploit
for filename in $ids_outputs/exploit_*.out; do 
    echo "start evaluating $(basename $filename)" >> $bashlog
    $EVAL_values \
        --output $eval_out/$(basename $filename).out \
        --attacks $attacks/attacks-exploit_ms08_netapi_modbus_6RTU_with_operate.json \
        --timed-dataset true \
        --log INFO \
        --logfile $eval_out/$(basename $filename).log \
        $filename;

    echo "finished evaluating $(basename $filename)" >> $bashlog
    echo "start plotting $(basename $filename)" >> $bashlog

    $EVAL_graph \
        --output $eval_out/$(basename $filename).picture \
        --attacks $attacks/attacks-exploit_ms08_netapi_modbus_6RTU_with_operate.json \
        --dataset "Lemay 6RTU" \
        --title "Lemay 6RTU $(basename $filename)" \
        --log INFO \
        --logfile $eval_out/$(basename $filename).picture.log \
        $filename;

    echo "finished plotting $(basename $filename)" >> $bashlog
done

# Moving files
for filename in $ids_outputs/moving_files_*.out; do 
    echo "start evaluating $(basename $filename)" >> $bashlog
    $EVAL_values \
        --output $eval_out/$(basename $filename).out \
        --attacks $attacks/attacks-moving_two_files_modbus_6RTU.json \
        --timed-dataset true \
        --log INFO \
        --logfile $eval_out/$(basename $filename).log \
        $filename;
    echo "finished evaluating $(basename filename)" >> $bashlog
    echo "start plotting $(basename $filename)" >> $bashlog

    $EVAL_graph \
        --output $eval_out/$(basename $filename).picture \
        --attacks $attacks/attacks-moving_two_files_modbus_6RTU.json \
        --dataset "Lemay 6RTU" \
        --title "Lemay 6RTU $(basename $filename)" \
        --log INFO \
        --logfile $eval_out/$(basename $filename).picture.log \
        $filename;

    echo "finished plotting $(basename $filename)" >> $bashlog
done

# fake command
for filename in $ids_outputs/fake_command_*.out; do 
    echo "start evaluating $(basename $filename)" >> $bashlog
    $EVAL_values \
        --output $eval_out/$(basename filename).out \
        --attacks $attacks/attacks-send_a_fake_command_modbus_6RTU_with_operate.json \
        --timed-dataset true \
        --log INFO \
        --logfile $eval_out/$(basename $filename).log \
        $filename;
    echo "finished evaluating $(basename $filename)" >> $bashlog
    echo "start plotting $(basename $filename)" >> $bashlog

    $EVAL_graph \
        --output $eval_out/$(basename $filename).picture \
        --attacks $attacks/attacks-send_a_fake_command_modbus_6RTU_with_operate.json \
        --dataset "Lemay 6RTU" \
        --title "Lemay 6RTU $(basename $filename)" \
        --log INFO \
        --logfile $eval_out/$(basename $filename).picture.log \
        $filename;

    echo "finished plotting $(basename $filename)" >> $bashlog
done