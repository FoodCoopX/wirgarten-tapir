export function getMaximumDate(dates: Date[]) {
  return dates.reduce(function (a, b) {
    return a > b ? a : b;
  });
}
