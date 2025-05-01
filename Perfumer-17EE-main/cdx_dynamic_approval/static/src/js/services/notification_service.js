/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
export const PushNotificationService = {
    dependencies: ["action", "bus_service", "notification"],

    start(env, { action, bus_service, notification}) {
        let activeNotifications = []; // Store references to active notifications
        bus_service.subscribe('my.notification', (notifications)  => {
                console.log("notification",notification)
                DisplayNotification(notifications);
           
        });

        /**
         * Displays the Calendar notification on user's screen
         */
        function DisplayNotification(notifications) {
            const removeNotification = notification.add(notifications.message, {
                title: notifications.title,
                type: 'info',
                sticky: true,
                onClose: () => {
                    activeNotifications = activeNotifications.filter(n => n !== removeNotification);
                },
                buttons: [
                    {
                        name: _t("Details"),
                        primary:true,
                        onClick: async () => {
                            await action.doAction({
                                type: 'ir.actions.act_window',
                                res_model: notifications.model_tech_name,
                                res_id: parseInt(notifications.rec_id),
                                views: [[false, 'form']],
                            });
                            removeNotification();
                        },
                    },
                    {
                        name: _t("Close All"),
                        onClick: () => closeAllNotifications(),
                    },
                ],
            });

            activeNotifications.push(removeNotification);
        }

        /**
         * Closes all active notifications
         */
        function closeAllNotifications() {
            activeNotifications.forEach(remove => remove());
            activeNotifications = [];
        }
    },
};

registry.category("services").add("PushNotification", PushNotificationService);
