COMMAND="python poker_hands.py"
${COMMAND}
watchmedo shell-command --patterns="*.py;*.jinja" \
    --command="${COMMAND}" \
    .