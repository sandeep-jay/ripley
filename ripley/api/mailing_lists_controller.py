"""
Copyright ©2023. The Regents of the University of California (Regents). All Rights Reserved.

Permission to use, copy, modify, and distribute this software and its documentation
for educational, research, and not-for-profit purposes, without fee and without a
signed licensing agreement, is hereby granted, provided that the above copyright
notice, this paragraph and the following two paragraphs appear in all copies,
modifications, and distributions.

Contact The Office of Technology Licensing, UC Berkeley, 2150 Shattuck Avenue,
Suite 510, Berkeley, CA 94720-1620, (510) 643-7201, otl@berkeley.edu,
http://ipira.berkeley.edu/industry-info for commercial licensing opportunities.

IN NO EVENT SHALL REGENTS BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL,
INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT OF
THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF REGENTS HAS BEEN ADVISED
OF THE POSSIBILITY OF SUCH DAMAGE.

REGENTS SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE
SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, PROVIDED HEREUNDER IS PROVIDED
"AS IS". REGENTS HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES,
ENHANCEMENTS, OR MODIFICATIONS.
"""

from datetime import datetime

from flask import current_app as app, request
from ripley.api.errors import BadRequestError, ResourceNotFoundError
from ripley.api.util import canvas_role_required, csv_download_response
from ripley.externals import canvas
from ripley.lib.http import tolerant_jsonify
from ripley.models.mailing_list import MailingList
from ripley.models.mailing_list_members import MailingListMembers


@app.route('/api/mailing_lists/<canvas_site_id>')
@canvas_role_required('TeacherEnrollment', 'TaEnrollment', 'Lead TA', 'Reader')
def mailing_lists(canvas_site_id):
    course = canvas.get_course(canvas_site_id)
    if course:
        mailing_list = MailingList.find_by_canvas_site_id(canvas_site_id) if course else None
        return tolerant_jsonify(mailing_list.to_api_json() if mailing_list else None)
    else:
        raise ResourceNotFoundError(f'No bCourses site with ID "{canvas_site_id}" was found.')


@app.route('/api/mailing_lists/<canvas_site_id>/create', methods=['POST'])
@canvas_role_required('TeacherEnrollment', 'TaEnrollment', 'Lead TA', 'Reader')
def create_mailing_lists(canvas_site_id):
    try:
        params = request.get_json()
        list_name = params.get('name')
        mailing_list = MailingList.create(
            canvas_site_id=canvas_site_id,
            list_name=(list_name or '').strip() or None,
        )
        return tolerant_jsonify(mailing_list.to_api_json())
    except ValueError as e:
        raise BadRequestError(str(e))


@app.route('/api/mailing_lists/<canvas_site_id>/suggested_name')
@canvas_role_required('TeacherEnrollment', 'TaEnrollment', 'Lead TA', 'Reader')
def get_suggested_mailing_list_name(canvas_site_id):
    return tolerant_jsonify(MailingList.get_suggested_name(canvas_site_id))


@app.route('/api/mailing_lists/<canvas_site_id>/download/welcome_email_log')
@canvas_role_required('TeacherEnrollment', 'TaEnrollment', 'Lead TA', 'Reader')
def download_welcome_email_log(canvas_site_id):
    mailing_list = MailingList.find_by_canvas_site_id(canvas_site_id)
    if mailing_list:
        now = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        rows = []
        mailing_list_members = MailingListMembers.get_mailing_list_members(mailing_list_id=mailing_list.id)
        for member in mailing_list_members:
            rows.append({
                'Name': f'{member.first_name} {member.last_name}',
                'Email address': member.email_address,
                'Message sent': member.welcomed_at,
                'Current member': 'N' if member.deleted_at else 'Y',
            })
        return csv_download_response(
            rows=rows,
            filename=f'{canvas_site_id}-welcome-messages-log-{now}.csv',
            fieldnames=['Name', 'Email address', 'Message sent', 'Current member'],
        )
    else:
        raise ResourceNotFoundError(f'No mailing list found for Canvas course {canvas_site_id}')


@app.route('/api/mailing_lists/<canvas_site_id>/populate', methods=['POST'])
@canvas_role_required('TeacherEnrollment', 'TaEnrollment', 'Lead TA', 'Reader')
def populate_mailing_lists(canvas_site_id):
    mailing_list = MailingList.find_by_canvas_site_id(canvas_site_id)
    if mailing_list:
        mailing_list, update_summary = MailingList.populate(mailing_list=mailing_list)
        return tolerant_jsonify({
            'mailingList': mailing_list.to_api_json(),
            'summary': update_summary,
        })
    else:
        raise ResourceNotFoundError(f'No mailing list found for Canvas course {canvas_site_id}')
