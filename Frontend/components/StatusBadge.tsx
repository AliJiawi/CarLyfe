import type { Status } from "@/lib/types";
import { STATUS_LABEL } from "@/lib/format";

/** Small dot + label. Colour is only ever the dot; the text carries the meaning. */
export function StatusBadge({ status }: { status: Status }) {
  return (
    <span className="status">
      <span className={`dot dot-${status}`} aria-hidden="true" />
      {STATUS_LABEL[status]}
    </span>
  );
}
