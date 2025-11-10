# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request, Response


class AccountJournalData(http.Controller):

    @http.route('/cancel_old_picking', type='http', auth='none', method=['POST'], csrf=False)
    def cancel_old_picking(self, **kw):
        if request.httprequest.method == 'POST':
            picking_type_ids = request.env['stock.picking.type'].sudo().with_context(active_test=False).search(
                [('warehouse_id', 'in', [343, 317, 337, 318, 320, 319, 290, 411, 334, 368, 442])])
            move_ids = request.env['stock.move'].sudo().search([
                ('picking_type_id', 'in', picking_type_ids.ids),
                ('state', 'not in', ('done', 'cancel'))])
            for move_id in move_ids:
                move_id.picking_id.action_cancel()
            # ids = [7975, 7984, 7988, 9221, 11388, 11389, 11390, 11391, 11556, 21663, 21691, 21692, 21694, 21697, 21698,
            #        21712, 21820, 21821, 22395, 22428, 22429, 22498, 22499, 22500, 22965, 22966, 22967, 23000, 24178,
            #        24191, 25132, 25374, 25375, 25376, 25395, 25396, 25566, 25567, 25568, 26074, 26075, 26725, 26726,
            #        26727, 26728, 26783, 26987, 27276, 27277, 27278, 27279, 27608, 28131, 28132, 28133, 28134, 28135,
            #        28144, 28145, 28146, 28796, 30007, 30823, 30824, 30848, 30968, 30969, 31032, 31033, 31034, 31066,
            #        31532, 31533, 31534, 32304, 32305, 32420, 32469, 32470, 32998, 32999, 33057, 33058, 33183, 33271,
            #        33291, 33292, 33302, 33303, 33333, 33338, 33444, 33445, 33474, 33475, 33686, 33687, 33688, 33701,
            #        33702, 33703, 34528, 34529, 34743, 35228, 35954, 35955, 36011, 36064, 36065, 36066, 36067, 36068,
            #        36682, 36789, 36800, 36803, 36814, 37103, 37281, 37302, 37303, 37304, 37305, 37795, 37796, 37984,
            #        38592, 38593, 39201, 39387, 39388, 39398, 39399, 41534, 41624, 41693, 41726, 41727, 41983, 41984,
            #        41985, 41986, 41987, 42121, 43469, 43470, 43489, 45294, 45329, 45934, 46582, 46606, 46643, 46769,
            #        47055, 47088, 47119, 47120, 49253, 49254, 49571, 49689, 51453, 53200, 53201, 53732, 53733, 55473,
            #        55474, 55475, 55476, 55477, 55478, 55479, 60574, 60800, 63713, 63714, 64247, 64471, 64472, 64473,
            #        64623, 65621, 65622, 65704, 65999, 66577, 67346, 67347, 67905, 67906, 68410, 68411, 68428, 69168,
            #        69169, 70479, 70480, 71497, 71866, 71867, 73135, 74094, 74095, 74308, 74309, 74310, 74311, 74360,
            #        76203, 78440, 78441, 78442, 78443, 78444, 80387, 80388, 80389, 81153, 81154, 81155, 81156, 81279,
            #        81280, 82218, 82219, 82220, 83430, 83431, 83541, 84177, 84178, 84461, 85238, 85239, 85240, 85241,
            #        85242, 86548, 86549, 86550, 90839, 90840, 91114, 91115, 91667, 91668, 93356, 93357, 95394, 97867,
            #        97868, 97869, 97870, 97871, 98838, 99875, 99928, 99929, 100643, 100644, 102515, 102516, 102940,
            #        104629, 104630, 104876, 104877, 105953, 105954, 105955, 105998, 106279, 106280, 107199, 107586,
            #        107587, 107588, 109825, 113770, 118024, 69125, 69127, 69128, 69129, 69516, 69517, 69950, 69951,
            #        69952, 69953, 70726, 70727, 70728, 70729, 75226, 37440, 37443, 37444, 37445, 37446, 37447, 37448,
            #        37449, 37450, 37451, 37452, 37453, 37454, 37455, 37459, 37460, 37461, 41251, 41254, 41255, 41265,
            #        41266, 41267, 41269, 41271, 41411, 41412, 42556, 42579, 42580, 42582, 42681, 42682, 42705, 42706,
            #        42728, 42729, 42742, 42754, 42812, 42816, 42818, 42967, 42968, 42976, 42977, 42978, 42981, 43644,
            #        44506, 44510, 44605, 44629, 45360, 45361, 45606, 45730, 45731, 46174, 46175, 46176, 46191, 46192,
            #        46240, 47264, 47265, 47296, 47346, 47362, 47363, 47703, 47899, 47900, 47901, 47902, 48772, 49697,
            #        49698, 49703, 49704, 50147, 50216, 50310, 50317, 50344, 50345, 50346, 50707, 51377, 52424, 52549,
            #        52550, 52579, 52580, 53184, 53185, 53186, 55131, 55133, 55134, 55334, 55422, 55426, 55427, 55489,
            #        55490, 55494, 56743, 56833, 56834, 57327, 57328, 57333, 57334, 57340, 57816, 57817, 57827, 57833,
            #        58188, 58198, 58199, 58200, 58607, 59097, 59311, 59312, 59776, 59777, 59781, 61427, 61428, 61429,
            #        61430, 61431, 61435, 61466, 61467, 61948, 61988, 62006, 62007, 62520, 63695, 63696, 64235, 64238,
            #        64452, 64485, 64778, 64779, 66637, 66648, 67344, 67345, 68248, 68249, 68269, 68791, 68792, 69011,
            #        69012, 69106, 69107, 69108, 69111, 69112, 69113, 69114, 69115, 69595, 70005, 70513, 70514, 70538,
            #        70964, 70968, 71562, 71861, 72252, 72253, 72264, 72265, 72266, 72267, 72556, 73042, 73043, 73044,
            #        73048, 73049, 73050, 73757, 73758, 73819, 73820, 73821, 73822, 73823, 73824, 73825, 73875, 73876,
            #        74229, 74230, 74231, 74232, 74233, 74234, 74238, 74255, 74256, 74259, 74273, 74274, 74298, 74979,
            #        74982, 75046, 75228, 75229, 76096, 76128, 76258, 76271, 77667, 77795, 77796, 77797, 78035, 78047,
            #        78049, 78082, 78083, 78132, 78133, 78245, 78278, 78287, 78288, 78713, 79627, 79777, 80220, 80221,
            #        80222, 80223, 80237, 80238, 80311, 80323, 80324, 81022, 81023, 81024, 81025, 81026, 81027, 81429,
            #        81430, 81431, 81432, 81468, 81469, 81691, 81798, 82108, 82109, 82213, 82229, 82265, 82266, 82920,
            #        82921, 83842, 83843, 83844, 84053, 84054, 84160, 84161, 84162, 84163, 84164, 84168, 84169, 84170,
            #        84197, 84246, 84250, 84316, 84651, 84671, 85221, 85228, 85262, 85263, 85269, 85278, 85699, 85739,
            #        85814, 85815, 85816, 85817, 85818, 85819, 85820, 85821, 85822, 85823, 85824, 86091, 86092, 86093,
            #        86117, 86120, 86122, 86123, 86124, 86127, 86749, 86782, 86783, 87049, 87085, 87086, 87090, 87091,
            #        87092, 87465, 87466, 87541, 87549, 87588, 87607, 87861, 87862, 87868, 90257, 90280, 90281, 90282,
            #        90287, 90288, 90289, 90290, 90294, 90295, 90345, 90358, 90680, 90693, 90694, 90695, 90696, 90723,
            #        90724, 90725, 90774, 90781, 90783, 90914, 90915, 90941, 91152, 91153, 91157, 91158, 91179, 91203,
            #        91204, 91220, 91227, 91228, 91490, 91491, 91972, 91973, 92134, 92138, 92139, 92140, 92219, 92230,
            #        92231, 92506, 92507, 92986, 92989, 93084, 93090, 93096, 93097, 93274, 93316, 93326, 93327, 93328,
            #        93329, 93330, 93331, 93332, 93333, 93334, 93335, 93336, 93342, 94681, 94682, 95035, 95036, 95180,
            #        95213, 95214, 95360, 96336, 96349, 96350, 96511, 96512, 96518, 96650, 96705, 96706, 96715, 96716,
            #        96717, 96718, 96719, 96720, 96721, 96722, 97064, 97065, 97759, 97763, 98086, 98519, 98533, 98543,
            #        98544, 98545, 98626, 98744, 98780, 98812, 99430, 99431, 99678, 99700, 100224, 100237, 100656, 100664,
            #        100665, 100670, 101159, 101210, 101233, 101234, 101263, 101386, 101387, 101388, 101389, 101404,
            #        102834, 102835, 102837, 102889, 102890, 102906, 102907, 102911, 102912, 103068, 103069, 103070,
            #        103071, 103093, 103114, 103115, 103233, 103234, 103250, 103252, 103253, 103494, 103495, 104294,
            #        105030, 105031, 105032, 105060, 105092, 105095, 105135, 105136, 105414, 105415, 106705, 106750,
            #        106755, 106786, 107091, 107133, 107592, 107593, 108909, 109691, 109692, 109702, 109897, 111356,
            #        111357, 111494, 111753, 111754, 113178, 113268, 113272, 113538, 113967, 114027, 114592, 114711,
            #        114773, 114774, 115170, 37463, 37472, 37473, 37880, 37881, 63656, 63657, 63658, 63660, 63661, 63663,
            #        63664, 63665, 63668, 63669, 63673, 63674, 63675, 63676, 63684, 63685, 63686, 64249, 64250, 64251,
            #        66566, 66567, 66587, 66588, 66605, 66617, 67751, 67752, 68243, 68244, 68311, 68795, 69373, 69374,
            #        69417, 69469, 69518, 69564, 69589, 69596, 69597, 69621, 69980, 70398, 70399, 70481, 70484, 70755,
            #        70763, 70803, 70804, 70949, 70950, 70951, 71031, 71473, 71824, 71835, 72212, 72654, 73408, 73409,
            #        73830, 74061, 74100, 74107, 74158, 74547, 74548, 74604, 74998, 75489, 76282, 76524, 76538, 76539,
            #        77779, 78007, 78105, 78309, 78696, 79555, 79625, 80245, 80263, 80611, 80612, 81126, 81127, 81166,
            #        81708, 82261, 82658, 82659, 82680, 82955, 82956, 83167, 83812, 84071, 84155, 84284, 84285, 84325,
            #        84326, 84780, 85005, 85006, 85007, 85205, 85633, 85662, 85763, 86056, 86128, 86554, 86555, 86806,
            #        86807, 86808, 87051, 87452, 87462, 87519, 87561, 87562, 87563, 87700, 87914, 88426, 88773, 88776,
            #        89320, 89324, 89469, 90247, 90300, 90493, 90690, 90691, 91461, 91939, 91940, 92206, 92512, 93047,
            #        93048, 93049, 93094, 93628, 94408, 94468, 94677, 95024, 95154, 95199, 95207, 95235, 96329, 96656,
            #        97051, 97090, 98079, 98523, 98524, 98525, 98595, 98969, 99530, 99532, 99701, 100124, 100161, 100472,
            #        100473, 101160, 101192, 101361, 101834, 102287, 102288, 102672, 102838, 102910, 103469, 103798,
            #        104241, 104511, 105084, 105344, 105377, 106765, 107584, 108354, 108709, 109169, 109680, 110060,
            #        110066, 110206, 110270, 111049, 111759, 113971, 114576, 115141, 115144, 115156, 116057, 116970,
            #        117201, 117288, 30666, 41492, 42615, 42616, 42642, 42685, 42686, 42687, 42719, 42720, 42737, 42738,
            #        42746, 42801, 42802, 42817, 43365, 43404, 43406, 43473, 43525, 43526, 43630, 44365, 44672, 44682,
            #        45337, 45371, 45670, 45679, 45680, 45681, 45682, 46257, 46259, 46263, 47324, 47325, 47326, 47327,
            #        47352, 47353, 47364, 47400, 47401, 47711, 47867, 47868, 47871, 47872, 48328, 48511, 48736, 48737,
            #        48757, 48758, 48759, 48877, 49463, 49677, 49693, 50083, 50111, 50128, 50129, 50137, 50252, 50306,
            #        50307, 50689, 50751, 50755, 50756, 50767, 51389, 51427, 51459, 52052, 52053, 52442, 52449, 52450,
            #        52521, 52522, 52677, 52678, 52688, 52831, 54328, 55283, 55284, 55310, 55313, 55357, 55383, 55403,
            #        57318, 57842, 57843, 57955, 57956, 59098, 59099, 59509, 59510, 59511, 59520, 59521, 59522, 59578,
            #        60247, 60258, 60259, 60264, 60293, 60294, 60377, 60426, 60468, 60469, 60589, 62009, 62558, 62586,
            #        63212, 63653, 63761, 64230, 64239, 64240, 64319, 64320, 65265, 65275, 65281, 65595, 66010, 66578,
            #        66579, 66580, 66586, 66598, 66614, 66638, 66670, 66824, 66987, 66990, 67022, 67023, 67024, 68256,
            #        68259, 68260, 68261, 68480, 68481, 68790, 68809, 69337, 69338, 69339, 69340, 69341, 69369, 69420,
            #        69490, 69505, 70177, 70178, 70189, 70385, 70818, 71575, 71872, 72629, 72630, 72638, 72639, 74128,
            #        74129, 74152, 74199, 74881, 74976, 74977, 74985, 75256, 75257, 75258, 75937, 75938, 75939, 75943,
            #        75944, 75946, 75947, 76060, 76257, 76563, 76572, 76965, 76966, 77525, 77625, 78757, 78758, 78793,
            #        79596, 79780, 80069, 80244, 80292, 80293, 80620, 81181, 81216, 81300, 81301, 82101, 82236, 82256,
            #        82257, 83391, 83392, 83482, 83725, 83813, 83814, 83815, 83824, 84098, 84099, 84112, 84146, 84157,
            #        84232, 85059, 85726, 85734, 85770, 85887, 86322, 86323, 86367, 86821, 86822, 87460, 87554, 87555,
            #        87556, 87564, 87865, 87866, 87870, 88078, 89490, 90311, 90554, 90767, 90768, 90769, 91276, 91914,
            #        91992, 91993, 92199, 92518, 92519, 93089, 94276, 94396, 94407, 94658, 94659, 95160, 95161, 95162,
            #        95244, 95335, 95468, 96539, 96589, 96599, 96600, 96608, 96609, 96797, 97055, 97349, 97350, 97477,
            #        97478, 97497, 97533, 97616, 97617, 97796, 97797, 97857, 98062, 98509, 98510, 98511, 98513, 98565,
            #        98851, 99423, 99695, 99702, 99716, 99717, 99817, 99899, 100002, 100119, 100120, 100123, 100214,
            #        100295, 100300, 101177, 101611, 101845, 102370, 102640, 102926, 103313, 104214, 104283, 105111,
            #        105112, 105349, 105421, 105422, 105423, 105438, 105983, 106758, 106759, 106973, 107099, 107221,
            #        107625, 108375, 108398, 108575, 108595, 108618, 108830, 108926, 108927, 109173, 109684, 109685,
            #        109686, 109687, 109748, 109878, 110200, 110225, 111060, 111064, 111342, 111343, 111344, 111355,
            #        111586, 111606, 112815, 112873, 112874, 113479, 113481, 113482, 113530, 113542, 113547, 113782,
            #        114581, 114582, 114616, 114617, 114652, 114676, 114677, 114720, 114721, 114722, 114852, 115116,
            #        115142, 115143, 115157, 115857, 115858, 115859, 115860, 116059, 116387, 116388, 117991]
            # stock_moves = request.env['stock.move'].sudo().search([('id', 'in', ids)])
            # for stock_move in stock_moves:
            #     stock_move.picking_id.action_cancel()
            return "Success"

    @http.route('/remove_default_journal', type='http', auth='none', method=['POST'], csrf=False)
    def remove_default_journal(self, **kw):
        if request.httprequest.method == 'POST':
            operators = request.env['res.company'].sudo().with_context(active_test=False).search([])
            for operator in operators:
                check_journal = request.env['account.journal'].sudo().search(
                    [('code', '=', 'CHK1'), ('company_id', '=', operator.id)])
                if check_journal:
                    check_journal.unlink()
                credit_card_journal = request.env['account.journal'].with_user(1).search(
                    [('code', '=', 'CRD1'), ('company_id', '=', operator.id)])
                if credit_card_journal:
                    credit_card_journal.unlink()
                wire_transfer_journal = request.env['account.journal'].sudo().search(
                    [('code', '=', 'WRT1'), ('company_id', '=', operator.id)])
                if wire_transfer_journal:
                    wire_transfer_journal.unlink()
                write_off_journal = request.env['account.journal'].sudo().search(
                    [('code', '=', 'WRO1'), ('company_id', '=', operator.id)])
                if write_off_journal:
                    write_off_journal.unlink()
                advance_journal = request.env['account.journal'].sudo().search(
                    [('code', '=', 'ADV1'), ('company_id', '=', operator.id)])
                if advance_journal:
                    advance_journal.unlink()
            return "Success"
        else:
            return "Failed"

    @http.route('/remove_default_coa', type='http', auth='none', method=['POST'], csrf=False)
    def remove_default_coa(self, **kw):
        if request.httprequest.method == 'POST':
            operators = request.env['res.company'].sudo().with_context(active_test=False).search([])
            for operator in operators:
                check_coa = request.env['account.account'].sudo().search(
                    [('name', '=', 'Check'), ('company_id', '=', operator.id)])
                if check_coa:
                    check_coa.unlink()
                credit_card_coa = request.env['account.account'].with_user(1).search(
                    [('name', '=', 'Credit Card'), ('company_id', '=', operator.id)])
                if credit_card_coa:
                    credit_card_coa.unlink()
                wire_transfer_coa = request.env['account.account'].sudo().search(
                    [('name', '=', 'Wire Transfer'), ('company_id', '=', operator.id)])
                if wire_transfer_coa:
                    wire_transfer_coa.unlink()
                write_off_coa = request.env['account.account'].sudo().search(
                    [('name', '=', 'Write Off'), ('company_id', '=', operator.id)])
                if write_off_coa:
                    write_off_coa.unlink()
                advance_coa = request.env['account.account'].sudo().search(
                    [('name', '=', 'Advance'), ('company_id', '=', operator.id)])
                if advance_coa:
                    advance_coa.unlink()
            return "Success"
        else:
            return "Failed"

    @http.route('/default_payment_mode', type='http', auth='none', method=['POST'], csrf=False)
    def create_default_payment(self, **kw):
        if request.httprequest.method == 'POST':
            operators = request.env['res.company'].sudo().with_context(active_test=False).search([])
            for operator in operators:
                check_payment = request.env['account.payment.mode'].sudo().search(
                    [('name', '=', 'Check'), ('type', '=', 'check'), ('operator_id', '=', operator.id)])
                if not check_payment:
                    check_payment_ctx = {
                        'name': 'Check',
                        'type': 'check',
                        'operator_id': operator.id
                    }
                    request.env['account.payment.mode'].with_user(1).create(check_payment_ctx)
                cash_payment = request.env['account.payment.mode'].sudo().search(
                    [('name', '=', 'Cash'), ('type', '=', 'cash'), ('operator_id', '=', operator.id)])
                if not cash_payment:
                    cash_payment_ctx = {
                        'name': 'Cash',
                        'type': 'cash',
                        'operator_id': operator.id
                    }
                    request.env['account.payment.mode'].with_user(1).create(cash_payment_ctx)
                credit_card_payment = request.env['account.payment.mode'].sudo().search(
                    [('name', '=', 'Credit Card'), ('type', '=', 'credit_card'), ('operator_id', '=', operator.id)])
                if not credit_card_payment:
                    credit_card_payment_ctx = {
                        'name': 'Credit Card',
                        'type': 'credit_card',
                        'operator_id': operator.id
                    }
                    request.env['account.payment.mode'].with_user(1).create(credit_card_payment_ctx)
                wire_transfer_payment = request.env['account.payment.mode'].sudo().search(
                    [('name', '=', 'Wire Transfer'), ('type', '=', 'wire_transfer'), ('operator_id', '=', operator.id)])
                if not wire_transfer_payment:
                    wire_transfer_payment_ctx = {
                        'name': 'Wire Transfer',
                        'type': 'wire_transfer',
                        'operator_id': operator.id
                    }
                    request.env['account.payment.mode'].with_user(1).create(wire_transfer_payment_ctx)
                write_off_payment = request.env['account.payment.mode'].sudo().search(
                    [('name', '=', 'Write Off'), ('type', '=', 'write_off'), ('operator_id', '=', operator.id)])
                if not write_off_payment:
                    write_off_payment_ctx = {
                        'name': 'Write Off',
                        'type': 'write_off',
                        'operator_id': operator.id
                    }
                    request.env['account.payment.mode'].with_user(1).create(write_off_payment_ctx)
                advance_payment = request.env['account.payment.mode'].sudo().search(
                    [('name', '=', 'Advance'), ('type', '=', 'advance'), ('operator_id', '=', operator.id)])
                if not advance_payment:
                    advance_payment_ctx = {
                        'name': 'Advance',
                        'type': 'advance',
                        'operator_id': operator.id
                    }
                    request.env['account.payment.mode'].with_user(1).create(advance_payment_ctx)
            return "Success"
        else:
            return "Failed"

    @http.route('/default_receivable', type='http', auth='none', method=['POST'], csrf=False)
    def default_receivable_update(self, **kw):
        if request.httprequest.method == 'POST':
            operator_ids = request.env['res.company'].sudo().with_context(active_test=False).search([])
            for operator_id in operator_ids:
                default_receivable = request.env['default.receivable'].sudo().search(
                    [('operator_id', '=', operator_id.id)])
                if not default_receivable:
                    request.env['default.receivable'].with_user(1).create({'operator_id': operator_id.id})
            return "Success"
        else:
            return "Failed"

    @http.route('/seq_update', type='http', auth='none', method=['POST'], csrf=False)
    def create_default_journal(self, **kw):
        if request.httprequest.method == 'POST':
            operators = request.env['res.company'].sudo().with_context(active_test=False).search([])
            for operator in operators:
                inv_journals = request.env['account.journal'].sudo().search(
                    [('code', '=', 'INV'), ('company_id', '=', operator.id)])
                for inv_journal in inv_journals:
                    inv_journal.sequence_id.with_user(1).write({'inv_seq': True})
                    inv_journal.refund_sequence_id.with_user(1).write({'inv_refund_seq': True})
                bill_journals = request.env['account.journal'].sudo().search(
                    [('code', '=', 'BILL'), ('company_id', '=', operator.id)])
                for bill_journal in bill_journals:
                    bill_journal.sequence_id.with_user(1).write({'bill_seq': True})
                    bill_journal.refund_sequence_id.with_user(1).write({'bill_refund_seq': True})
            return "Success"
        else:
            return "Failed"
