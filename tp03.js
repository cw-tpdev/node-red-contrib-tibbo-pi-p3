module.exports = function (RED) {
    "use strict";

    // #03 Two low-power relays

    var TpCommon = require('./tpCommon');

    function TP_03_OutNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp03_out", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput();
    }
    RED.nodes.registerType("Tibbit-#03 out", TP_03_OutNode);
}
