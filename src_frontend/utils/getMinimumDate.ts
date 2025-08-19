export function getMinimumDate(dates: Date[]) {
  return dates.reduce(function (a, b) {
    return a < b ? a : b;
  });
}
