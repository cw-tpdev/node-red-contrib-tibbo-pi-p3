module.exports = function (RED) {
    "use strict";

    // #59 Two 24V PNP isolated open collector outputs

    var TpCommon = require('./tpCommon');

    function TP_59_OutNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp59_out", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput();
    }
    RED.nodes.registerType("Tibbit-#59 out", TP_59_OutNode);
}
