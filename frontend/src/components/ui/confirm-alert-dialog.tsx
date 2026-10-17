import * as React from "react";
import {
  AlertDialog,
  alertDialogButtonBase,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { cn } from "@/lib/utils";

export interface ConfirmAlertDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: React.ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void | Promise<void>;
  destructive?: boolean;
}

export function ConfirmAlertDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  onConfirm,
  destructive = false,
}: ConfirmAlertDialogProps) {
  const [pending, setPending] = React.useState(false);

  React.useEffect(() => {
    if (!open) setPending(false);
  }, [open]);

  const handleConfirm = React.useCallback(() => {
    setPending(true);
    void (async () => {
      try {
        await Promise.resolve(onConfirm());
        onOpenChange(false);
      } finally {
        setPending(false);
      }
    })();
  }, [onConfirm, onOpenChange]);

  return (
    <AlertDialog open={open} onOpenChange={(v) => !pending && onOpenChange(v)}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription className="text-left">
            {description}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={pending}>
            {cancelLabel}
          </AlertDialogCancel>
          <button
            type="button"
            disabled={pending}
            onClick={handleConfirm}
            className={cn(
              alertDialogButtonBase,
              "min-w-[6.5rem]",
              destructive
                ? "bg-red-600 text-white hover:bg-red-700"
                : "bg-indigo-600 text-white hover:bg-indigo-700",
            )}
          >
            {pending ? "Please wait…" : confirmLabel}
          </button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
