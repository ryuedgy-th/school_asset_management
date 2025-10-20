/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Client action to copy signature link to clipboard
 * This action doesn't need a UI component - it just copies and shows notification
 */
async function copySignatureLinkAction(env, action) {
    const link = action.params.link;
    const expiryDate = action.params.expiry;

    try {
        // Modern clipboard API
        await navigator.clipboard.writeText(link);

        env.services.notification.add(
            `✅ Link copied to clipboard!\n\n${link}\n\nExpires: ${expiryDate}\n\nYou can now paste it in LINE or WhatsApp.`,
            {
                title: "Signature Link Copied",
                type: "success",
                sticky: false,
                duration: 10000,
            }
        );
    } catch (err) {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = link;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        document.body.appendChild(textArea);
        textArea.select();

        try {
            document.execCommand('copy');
            env.services.notification.add(
                `✅ Link copied!\n\n${link}\n\nExpires: ${expiryDate}`,
                {
                    title: "Signature Link Copied",
                    type: "success",
                    sticky: false,
                    duration: 10000,
                }
            );
        } catch (err2) {
            // If copy fails, show dialog with link to manually copy
            env.services.notification.add(
                `Copy this link manually:\n\n${link}\n\nExpires: ${expiryDate}`,
                {
                    title: "Signature Link",
                    type: "info",
                    sticky: false,
                    duration: 10000,
                }
            );
        } finally {
            document.body.removeChild(textArea);
        }
    }

    // Don't navigate - stay on current page
    return Promise.resolve();
}

registry.category("actions").add("copy_signature_link", copySignatureLinkAction);
