// Add !skip_pick command

const skipPickCommand = async (message) => {
    const schedule = await getSchedule(); // Fetch the current schedule
    const pickerIndex = schedule.findIndex(picker => picker.id === message.author.id);

    if (pickerIndex === -1) return message.reply("You are not in the schedule.");

    // Skip the next picker
    const nextPickerIndex = (pickerIndex + 1) % schedule.length;
    const newPickerIndex = (nextPickerIndex + 1) % schedule.length;

    // Shift the schedule
    const newSchedule = [...schedule.slice(0, nextPickerIndex), schedule[newPickerIndex], ...schedule.slice(nextPickerIndex + 1)];

    // Update the database with the new schedule
    await updateScheduleInDatabase(newSchedule);

    message.reply(`The next picker has been skipped. New schedule: ${newSchedule.join(', ')}`);
};

module.exports = { skipPickCommand };